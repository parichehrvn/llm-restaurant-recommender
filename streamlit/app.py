import streamlit as st
import requests


API_URL = 'http://fastapi:8000'

@st.cache_data
def get_suggestions(query):
    response = requests.get(f'{API_URL}/suggest?query={query}')
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        st.error('Failed to get suggestions')
        return None

@st.cache_data
def get_summary(res_name):
    response = requests.get(f'{API_URL}/summary/{res_name}')
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        st.error('Failed to get summary')
        return None


@st.cache_data
def get_answers(res_name, user_query):
    payload = {'query': user_query + f' in {res_name}', 'restaurant_name': res_name}
    response = requests.post(f'{API_URL}/query', json=payload)
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        st.error('Failed to fetch')
        return 'No answers available'


st.set_page_config(
    page_icon=':stew:',
    page_title='Restaurant Recommender',
    layout='wide'
)


if 'query' not in st.session_state:
    st.session_state['query'] = ''

if 'suggestion' not in st.session_state:
    st.session_state['suggestion'] = []

if 'active_window' not in st.session_state:
    st.session_state.active_window = None

if 'selected_restaurant' not in st.session_state:
    st.session_state['selected_restaurant'] = None

if 'messages' not in st.session_state:
    st.session_state['messages'] = []


st.title('Restaurant Recommender Chatbot')
st.caption('AI chatbot restaurant recommender')


def home():
    col1, col2 = st.columns([3, 1])

    query = col1.text_input('What do you look for?', label_visibility='collapsed', placeholder='eg: where can I find best pizza?')

    if col2.button(':mag_right: Search'):
       if query:
           st.session_state['query'] = query
           response = get_suggestions(query)
           st.session_state['suggestion'] = response
       else:
           st.warning('⚠️ Enter a valid query')

    if st.session_state['suggestion']:
        st.subheader('Recommendations')
        st.write(st.session_state['suggestion']['greeting'])

        for idx, suggestion in enumerate(st.session_state['suggestion']['suggestions']):
            col1, col2 = st.columns([1, 3])
            with col1:
                # Unique key for each button to avoid Streamlit key conflicts
                if st.button(suggestion['restaurant_name'], key=f'btn_{idx}'):
                    # if st.session_state['selected_restaurant'] == suggestion['restaurant_name']:
                    st.session_state['selected_restaurant'] = suggestion['restaurant_name']
                    st.session_state['messages'] = []
                    # else:
                    #     st.session_state['selected_restaurant'] = suggestion['restaurant_name']
                    #     st.session_state['messages'] = []

            with col2:
                st.write(suggestion['note'])

            if st.session_state['selected_restaurant'] == suggestion['restaurant_name']:
                summary = get_summary(suggestion['restaurant_name'])
                st.info(summary['conclusion'], icon='ℹ️')
                tab1, tab2, tab3, tab4, tab5 = st.tabs(['Must try dishes', 'Highlights', 'Things to be noted', 'Location', 'Rating'])
                with tab1:
                    for i in summary['must_try_dishes']:
                        st.write(f'🍽️ {i}')
                with tab2:
                    st.write(summary['highlights'])
                with tab3:
                    st.write(summary['notes'])
                with tab4:
                    st.write(summary['location'])
                with tab5:
                    st.write(summary['rating'])


def chat_bot():
    if st.session_state['selected_restaurant']:
        with st.sidebar:
            st.title(f'Ask questions about {st.session_state['selected_restaurant']}')
            user_input = st.chat_input('Type your question here...', key=f'chat_{st.session_state['selected_restaurant']}')
            if user_input:
                bot_response = get_answers(st.session_state['selected_restaurant'], user_input)
                bot_response = bot_response['answer']
                chat = [{'role': 'user', 'content': user_input}, {'role': 'assistant',
                                                                  'content': f':blue-background[{st.session_state["selected_restaurant"]}]: {bot_response}'}]
                st.session_state.messages.append(chat)
            chat_container = st.container()
            with chat_container:
                for chat in reversed(st.session_state.messages):
                    with st.container(border=True):
                        st.chat_message(chat[0]['role'], avatar='🧑').markdown(f'**{chat[0]['content']}**')

                    st.chat_message(chat[1]['role'], avatar='🤖').markdown(chat[1]['content'])


with st.spinner('Fetching your data...⌛'):
    home()
    chat_bot()