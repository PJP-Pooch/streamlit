import streamlit as st
import pandas as pd
import requests
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

# Function to clear input fields
def clear_form():
    st.session_state.api_key = ""
    st.session_state.cse_id = ""
    st.session_state.site = ""
    st.session_state.keywords = ""
    st.session_state.target_urls = ""

# Streamlit app title
st.title("Google Custom Search Results")

# Button to clear form
st.button("Clear Form", on_click=clear_form)

# Input fields for API key, CSE ID, and site
api_key = st.text_input("Enter your Google API key:", key='api_key')
cse_id = st.text_input("Enter your Custom Search Engine ID:", key='cse_id')
site = st.text_input("Enter the site (e.g., 'example.com'):", key='site')

# Input fields for keywords and target URLs
keywords = st.text_area("Enter keywords (one per line):", key='keywords')
target_urls = st.text_area("Enter corresponding target URLs (one per line):", key='target_urls')

if api_key and cse_id and site and keywords and target_urls:
    # Split the input into lists
    keyword_list = keywords.split('\n')
    target_url_list = target_urls.split('\n')

    if len(keyword_list) != len(target_url_list):
        st.error("The number of keywords must match the number of target URLs.")
    else:
        # Button to run the script
        if st.button("Run Script"):
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
                link_list = [result['link'] for result in results.get('items', [])]

                # If less than 10 links are returned, fill the rest with None
                while len(link_list) < 10:
                    link_list.append(None)

                # Append the list of links to the results dataframe
                results_df = pd.concat([results_df, pd.Series(link_list, name=index)], axis=1)

            # Transpose the results dataframe and set column names
            results_df = results_df.transpose()
            results_df.columns = [f'link{i+1}' for i in range(10)]

            # Concatenate the original dataframe with the results dataframe
            df = pd.concat([df, results_df], axis=1)

            # Write the updated dataframe to a CSV file and provide a download link
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            st.download_button(
                label="Download output CSV",
                data=output,
                file_name="output.csv",
                mime="text/csv"
            )

            st.write("Search completed and results are ready to download.")

            # Display the results in a static table
            st.write("Results Table:")
            st.dataframe(df)
