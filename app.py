import streamlit as st
from http.client import HTTPSConnection
from base64 import b64encode
from json import loads, dumps

class RestClient:
    domain = "api.dataforseo.com"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def request(self, path, method, data=None):
        connection = HTTPSConnection(self.domain)
        try:
            base64_bytes = b64encode(("%s:%s" % (self.username, self.password)).encode("ascii")).decode("ascii")
            headers = {'Authorization': 'Basic %s' % base64_bytes, 'Content-Encoding': 'gzip'}
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            return loads(response.read().decode())
        finally:
            connection.close()

# Streamlit app
st.title('SERP Groups API Client')

# Input fields for API credentials
username = st.text_input('Username')
password = st.text_input('Password', type='password')

# Input field for API endpoint and method
path = st.text_input('API Path', '/v3/serp/google/organic/live/advanced')
method = st.selectbox('HTTP Method', ['GET', 'POST'])

# Input field for request body (for POST requests)
data = st.text_area('Request Body (JSON format)', '{}')

# Button to make the API request
if st.button('Make API Request'):
    if username and password and path and method:
        client = RestClient(username, password)
        try:
            response = client.request(path, method, data if method == 'POST' else None)
            st.success('Request Successful')
            st.json(response)
        except Exception as e:
            st.error(f'Error: {e}')
    else:
        st.error('Please provide all required inputs')

# Run the Streamlit app
if __name__ == '__main__':
    st.run()
