from elasticsearch import Elasticsearch, exceptions
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import os
import spacy
import json
from dotenv import load_dotenv
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


# ---------------------- Config ---------------------- #
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("googleAIStudio")
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
INDEX_NAME = os.getenv("ES_INDEX", "restaurant_reviews")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GEN_MODEL = "gemini-1.5-flash"

# KNN config
K = 50
NUM_CANDIDATES = 200 # larger candidate pool improves recall

# ----------------- Clients ----------------- #
try:
    ES = Elasticsearch(ES_HOST)
except exceptions as e:
    print(f"Elasticsearch error: {e}")

genai.configure(api_key=GOOGLE_API_KEY)


def create_embedding(text):
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    try:
        embedding = embed_model.get_query_embedding(text)
        return embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def get_location(query):
    # Initialize SpaCy model
    try:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(query)
        locations = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
    except Exception as e:
        print(f"SpaCy error: {e}")
        locations = []

    # If SpaCy found locations, return them
    if locations:
        return ", ".join(locations)  # Use comma for clarity

    # Fallback to Gemini
    try:
        model = genai.GenerativeModel(GEN_MODEL)
        output_format = {
            "locations": ["string"],
            "error": "string"  # Optional error message if no locations found
        }
        prompt = f"""
            You are an NER model tasked with extracting locations from the following query: "{query}".
            A location can be a city, country, region, address, or any geographical entity.
            Return a JSON object in this format: {output_format}.
            - If locations are found, include them in the "locations" list.
            - If no locations are found, set "locations" to an empty list and provide a brief explanation in "error".
            - Do not include any other fields or explanations outside the JSON format.
            """
        response = model.generate_content(prompt)

        # Handle Gemini response (assuming it returns a JSON-like string)
        try:
            result = json.loads(response.text)  # Adjust based on actual response structure
            if result.get("locations"):
                return ", ".join(result["locations"])
            else:
                # print(f"Gemini error: {result.get('error', 'No locations found')}")
                return ""
        except json.JSONDecodeError:
            # print("Gemini response was not valid JSON")
            return ""
    except google_exceptions.GoogleAPIError as e:
        print(f"Gemini API error: {e}")
        return ""


def get_context(query):
    if not query or not isinstance(query, str):
        return []

    # Extract location from query
    location = get_location(query)

    vector = create_embedding(query)
    search_query = {
        "knn": {
            "field": "review_vector",
            "query_vector": vector,
            "k": 50,
            "num_candidates": 100
        },
        "_source": [
            "review",
            "metadata.restaurant_name",
            "metadata.location",
        ],  # Ensure nested fields are included
        "track_total_hits": True
    }

    # Add location filter if available
    if location:
        search_query["query"] = {
            "bool": {
                "should": [
                    {"match": {"metadata.location": location}},
                    {"match": {"metadata.address": location}}
                ],
                "minimum_should_match": 1
            }
        }

    result = ES.search(index=INDEX_NAME, body=search_query)

    # Deduplicate restaurants and format documents
    seen_restaurants = set()
    documents = []
    for doc in result["hits"]["hits"]:
        restaurant_name = doc["_source"].get("metadata", {}).get("restaurant_name", "")
        if restaurant_name not in seen_restaurants:
            seen_restaurants.add(restaurant_name)
            doc_content = {
                "restaurant_name": restaurant_name,
                "review": doc["_source"]["review"],
                "location": doc["_source"].get("metadata", {}).get("location", ""),
            }
            documents.append(json.dumps(doc_content))  # Structured JSON string
    return documents


def get_suggestions(query):
    if not query or not isinstance(query, str):
        return json.dumps([])

    # Get context documents
    documents = get_context(query)
    if not documents:
        return json.dumps([])

    try:
        model = genai.GenerativeModel(GEN_MODEL)

        # Define output format
        output_format = {
            'greeting': 'string',
            'suggestions': [
                {
                    'restaurant_name': 'string',
                    'note': 'string',
                    'conclusion': 'string'
                }
            ]
        }

        prompt = f"""
        You are a restaurant recommender. Suggest restaurants based on the user query : "{query}".
        Use the provided data to make recommendations.
        Only recommend restaurants with positive reviews (avoid negative sentiment).
        Do not recommend the same restaurant more than once.
        Return a JSON object in this format: {json.dumps(output_format)}.
        - First start with a greeting message. A short, friendly welcome message (1-2 sentences) tailored to the user's query, expressing enthusiasm for finding the best matches.
        - Each suggestion must include: restaurant_name, note (why it matches the query), conclusion (recommendation summary).
        - If no suitable restaurants are found, return:
          {{
            "suggestions": [],
            "reason": say your reason here
          }}
        - Do not include any other fields or explanations outside the JSON format.

        Data:
        {chr(10).join(documents)}
        """
        response = model.generate_content(prompt)

        # Parse and validate response
        try:
            result = response.text.split('```json')[1].split('```')[0]
            result = json.loads(result)
            if not isinstance(result.get('suggestions'), list):
                print("Invalid response format: 'suggestions' is not a list")
                return json.dumps([])
            return json.dumps(result)
        except json.JSONDecodeError:
            print("Gemini response was not valid JSON")
            return json.dumps([])
    except google_exceptions.GoogleAPIError as e:
        print(f"Gemini API error: {e}")
        return json.dumps([])


def get_res_reviews(restaurant_name):
    """
    Retrieve reviews for a specific restaurant from Elasticsearch.

    Args:
        restaurant_name (str): Name of the restaurant to query.

    Returns:
        list: List of review documents (as dictionaries) with restaurant_name, review, location, and address.
    """
    query = {
        'size': 50,
        'query':{
            'match':{
                'metadata.restaurant_name': restaurant_name
            }
        },
        "_source": [
            "review",
            "metadata.restaurant_name",
            "metadata.rating",
            "metadata.location",
        ],
    }
    result = ES.search(index=INDEX_NAME, body=query)
    reviews = []
    result = result["hits"]["hits"]
    for doc in result:
        reviews.append(doc['_source']['review'])

    documents = {
        "restaurant_name": restaurant_name,
        "reviews": "\n".join(reviews),
        "rating": result[0]["_source"].get("metadata", {}).get("rating", 0),
        "location": result[0]["_source"].get("metadata", {}).get("location", "")
    }
    return documents


def get_summary(restaurant_name):
    model = genai.GenerativeModel(GEN_MODEL)
    documents = get_res_reviews(restaurant_name)

    if not documents:
        return json.dumps({
            "restaurant_name": restaurant_name,
            "answer": "No reviews found for the restaurant"
        })

    try:

        output_format = {
            'restaurant_name': 'string',
            'must_try_dishes': 'list',
            'highlights': 'string',
            'notes': 'string',
            'conclusion': 'string',
            'rating': 'number'
        }

        prompt = f'''You are a restaurant recommender. 
        Your task is to analyze reviews for the restaurant '{restaurant_name}' and provide a structured summary based on the given reviews
        **Input Reviews**:
        {''.join(json.dumps(documents))}
        Return a JSON object in this format: {json.dumps(output_format)}.
        **Instructions**:
        1. Analyze the reviews to identify:
        - **Must try dishes:**: List specific dishes recommended based on the reviews, up to 5 dishes, if available. If no dishes are mentioned, state ""
        - **Highlights**: Provide a short and concise summary of positive aspects or strengths of the restaurant (e.g., ambiance, service, food quality), if available. If none, state ""
        - **notes**: Note any negative aspects or areas for improvement shortly and concisely(e.g., slow service, pricing), if available. If none, state ""
        - **Conclusion**: Provide a concise summary of the restaurant's overall experience based on the reviews.
        - **Rating**: For each restaurant, extract numerical ratings (e.g., 1 to 5 stars) from all provided reviews. Calculate the average rating, rounded to one decimal place. If no numerical ratings are available or if ratings are non-numerical, indicate 'No valid ratings found' for that restaurant.
        '''

        response = model.generate_content(prompt)
        try:
            result = response.text.split('```json')[1].split('```')[0]
            result = json.loads(result)
            result['location'] = documents['location']
            return json.dumps(result)
        except json.JSONDecodeError:
            print("Gemini response was not valid JSON")
            return json.dumps([])
    except Exception as e:
        print(f"Gemini API error: {e}")
        return json.dumps([])


def restaurant_qna(restaurant_name, query):
    """
    Answer a specific question about a restaurant based on its reviews.

    Args:
        restaurant_name (str): Name of the restaurant.
        query (str): User's question about the restaurant.

    Returns:
        str: JSON string with restaurant name and answer.
    """
    try:
        model = genai.GenerativeModel(GEN_MODEL)
        # Get reviews
        documents = get_res_reviews(restaurant_name)
        if not documents:
            return json.dumps({
                "restaurant_name": restaurant_name,
                "answer": "No reviews found for the restaurant"
            })
        # Define output format
        output_format = {
            "restaurant_name": "string",
            "answer": "string"
        }
        # Create prompt
        prompt = f"""                                                                                            
        You are a restaurant Q&A assistant. Answer the user's question about the restaurant '{restaurant_name}',
         based on user's query: '{query}'. 
        Use the provided reviews to formulate a precise and relevant answer. 
        **Input Reviews**:
        {''.join(json.dumps(documents))}                                    
        Return a JSON object in this format: {json.dumps(output_format)}.    
        **Instructions**:                                    
        - 'restaurant_name': The restaurant name ({restaurant_name}).                                                       
        - 'answer': The answer to the question, or an explanation if no relevant information is found.           
        - Do not include additional fields or explanations outside the JSON format.                                                                                                      
        """
        response = model.generate_content(prompt)
        try:
            result = response.text.split('```json')[1].split('```')[0]
            result = json.loads(result)
            return json.dumps(result)
        except json.JSONDecodeError:
            print("Gemini response was not valid JSON")
            return json.dumps([])
    except Exception as e:
        print(f"Gemini API error: {e}")
        return json.dumps([])