import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import io

# Function to search using Google Custom Search JSON API
def search(query, api_key, cse_id, **kwargs):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
    }
    params.update(kwargs)
    response = requests.get(url, params=params)
    return json.loads(response.text)

# Streamlit app title
st.title("Google Custom Search Results")

# Input fields for API key, CSE ID, and site
api_key = st.text_input("Enter your Google API key:")
cse_id = st.text_input("Enter your Custom Search Engine ID:")
site = st.text_input("Enter the site (e.g., 'example.com'):")

# Input fields for keywords and target URLs
keywords = st.text_area("Enter keywords (one per line):")
target_urls = st.text_area("Enter corresponding target URLs (one per line):")

if api_key and cse_id and site and keywords and target_urls:
    # Split the input into lists
    keyword_list = keywords.split('\n')
    target_url_list = target_urls.split('\n')

    if len(keyword_list) != len(target_url_list):
        st.error("The number of keywords must match the number of target URLs.")
    else:
        # Create a dataframe from the input lists
        df = pd.DataFrame({
            'keyword': keyword_list,
            'target_page': target_url_list
        })

        # Create a new dataframe to store results
        results_df = pd.DataFrame()

        for index, row in df.iterrows():
            # Search query
            query = f"site:{site} {row['keyword']} -inurl:{row['target_page']}"

            # Get the search results
            results = search(query, api_key, cse_id)

            # Extract the URLs of the search results
            link_list = [result['link'] for result in results.get('
