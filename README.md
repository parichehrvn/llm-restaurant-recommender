# llm-restaurant-recommender
Restaurant recommender chatbot using Retrieval-Augmented Generation (RAG) with LlamaIndex, Elasticsearch, Ollama, and Gemini. Interactive UI via Streamlit and FastAPI.
---

## Overview
Reading restaurant reviews can be overwhelming.They are often long, detailed, and time-consuming to go through. This chatbot, built on the **Yelp Open Dataset**, acts as a user’s assistant by analyzing reviews and providing clear, concise insights. It can recommend restaurants, answer specific questions, and highlight both positive and negative aspects of a restaurant to simplify the restaurant selection process.
It leverages **Elasticsearch** for semantic search, **Gemini LLM** for natural language generation, and **LlamaIndex** for RAG orchestration. The system is built with **FastAPI** for backend services and **Streamlit** for an interactive user interface.
---
![image](data/demo/demo.png)
---
##  Features

- Conversational restaurant recommendations.

- Context-aware responses powered by RAG.

- Semantic search with Elasticsearch + Ollama embeddings.

- Streamlit interface for easy interaction.

- Backend API built with FastAPI for modularity.
 
---
## Tech Stack

RAG Framework: LlamaIndex

Retriever / DB: Elasticsearch (Docker)

Embeddings: Ollama (all-minilm)

Generative Model: Gemini

Backend: FastAPI

UI: Streamlit

## Demo