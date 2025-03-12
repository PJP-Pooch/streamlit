import streamlit as st
import requests
import pandas as pd
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# Streamlit App Title
st.title("🔗 Internal Link Finder (Semantic SEO Tool)")

# Upload CSV file
uploaded_file = st.file_uploader("Upload CSV file with URLs", type=["csv"])

# If file is uploaded, process it
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    urls = df["URL"].dropna().tolist()
    
    # Display the uploaded URLs
    st.write("✅ Loaded", len(urls), "URLs")

    # Button to start processing
    if st.button("Find Internal Link Opportunities"):
        st.write("🔍 Fetching content & analyzing link structure...")

        # Progress bar
        progress_bar = st.progress(0)

        def get_page_content_and_links(url):
            """Fetch page content and extract all internal links."""
            try:
                response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                if "text/html" not in response.headers.get("Content-Type", ""):
                    return "", set()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract main content (all text within paragraphs)
                content = ' '.join([p.text for p in soup.find_all('p')]).strip()

                # Extract existing internal links
                base_domain = urlparse(url).netloc
                internal_links = {a['href'] for a in soup.find_all('a', href=True) if urlparse(a['href']).netloc == base_domain}

                return content, internal_links
            except:
                return "", set()

        # Step 1: Get page content and existing links
        page_data = {url: get_page_content_and_links(url) for url in urls}

        # Filter out empty pages
        filtered_urls = [url for url, content in page_data.items() if content[0].strip()]
        filtered_corpus = [page_data[url][0] for url in filtered_urls]

        if len(filtered_corpus) < 2:
            st.error("Not enough valid pages with content to compute similarity.")
            st.stop()

        # Step 2: Compute Similarity Scores for Content
        vectorizer = TfidfVectorizer(stop_words='english')
        X = vectorizer.fit_transform(filtered_corpus)
        similarity_matrix = X @ X.T  # Corrected TF-IDF computation

        # Step 3: Identify Internal Link Opportunities
        threshold = 0.15  # Adjust threshold for link relevance
        internal_link_suggestions = []

        for i, source_url in enumerate(filtered_urls):
            source_content, existing_links = page_data[source_url]

            for j, target_url in enumerate(filtered_urls):
                if i != j and similarity_matrix[i, j] > threshold and target_url not in existing_links:
                    internal_link_suggestions.append((source_url, target_url, similarity_matrix[i, j]))

            # Update progress bar
            progress_bar.progress((i + 1) / len(filtered_urls))

        # Step 4: Display Results
        results_df = pd.DataFrame(internal_link_suggestions, columns=["Source Page", "Suggested Internal Link", "Relevance Score"])
        st.write("✅ Internal Link Suggestions:")
        st.dataframe(results_df)

        # Step 5: Downloadable CSV
        csv_data = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv_data, "internal_link_suggestions.csv", "text/csv", key="download-csv")
