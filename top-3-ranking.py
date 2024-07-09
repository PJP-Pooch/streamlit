import streamlit as st
import pandas as pd
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
            base64_bytes = b64encode(
                ("%s:%s" % (self.username, self.password)).encode("ascii")
            ).decode("ascii")
            headers = {'Authorization': 'Basic %s' % base64_bytes, 'Content-Encoding': 'gzip'}
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            return loads(response.read().decode())
        finally:
            connection.close()

    def get(self, path):
        return self.request(path, 'GET')

    def post(self, path, data):
        if isinstance(data, str):
            data_str = data
        else:
            data_str = dumps(data)
        return self.request(path, 'POST', data_str)

def get_data(keyword, client, location_code, language_code, device, domain, num_results):
    post_data = {
        "data": [
            {
                "keyword": keyword,
                "location_code": location_code,
                "language_code": language_code,
                "device": device,
                "se_domain": domain,
                "num_results": num_results
            }
        ]
    }
    response = client.post("/v3/serp/google/organic/live/advanced", post_data)
    if response["status_code"] == 20000:
        return response["tasks"][0]["result"][0]["items"]
    else:
        st.error("Error: " + response["status_message"])
        return []

def analyze_results(results):
    if not results:
        st.warning("No results to analyze.")
        return pd.DataFrame()

    data = {
        "url": [],
        "keyword": []
    }
    
    for item in results:
        data["url"].append(item["url"])
        data["keyword"].append(item["keyword"])

    df = pd.DataFrame(data)
    analysis_df = df.groupby('url').agg({'keyword': lambda x: list(set(x))})
    analysis_df['count'] = analysis_df['keyword'].str.len()
    analysis_df.sort_values(by='count', ascending=False, inplace=True)
    return analysis_df

st.title("SEO Data Analysis")

# User Inputs
username = st.text_input("API Username")
password = st.text_input("API Password", type="password")
domain = st.text_input("Domain")
language = st.text_input("Language", value="English")  # Example: en for English
device = st.selectbox("Device", ["desktop", "mobile"], index=1)
num_results = st.number_input("Number of Results", min_value=1, max_value=10, value=3)
keywords = st.text_area("Keywords (one per line)").split('\n')

if st.button("Run Analysis"):
    client = RestClient(username, password)
    all_data = []

    for keyword in keywords:
        if keyword.strip():
            data = get_data(keyword.strip(), client, location, language, device, domain, num_results)
            all_data.extend(data)
    
    if all_data:
        df = pd.DataFrame(all_data)
        st.write("Raw Results", df)
        df.to_csv("output.csv", index=False)
        st.success("Raw analysis complete and saved to output.csv")

        analysis_df = analyze_results(all_data)
        st.write("Analysis Results", analysis_df)
        analysis_df.to_csv("most_common.csv")
        st.success("Analysis complete and saved to most_common.csv")
