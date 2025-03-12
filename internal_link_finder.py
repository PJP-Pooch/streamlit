import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Streamlit App Title
st.title("🔗 Internal Link Finder (From XML Sitemap)")

# User Input: XML Sitemap URL
sitemap_url = st.text_input("Enter your XML Sitemap URL", "")

# Button to start processing
if st.button("Find Internal Link Opportunities") and sitemap_url:

    st.write("🔍 Fetching URLs from the sitemap...")
    
    # Step 1: Fetch all URLs from XML Sitemap
    def get_sitemap_urls(sitemap_url):
        """Fetch and parse URLs from XML sitemap, filtering out non-HTML pages."""
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.content, "xml")  # Ensure correct XML parsing
        urls = [loc.text for loc in soup.find_all("loc")]

        # Filter out image URLs (e.g., Shopify CDN, PNG, JPG, etc.)
        html_urls = [url for url in urls if not url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"))]
        
        return html_urls

    urls = get_sitemap_urls(sitemap_url)
    st.write("✅ Found", len(urls), "valid HTML pages in the sitemap.")

    # Progress bar
    progress_bar = st.progress(0)

    # Step 2: Extract page content and existing internal links
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

    st.write("🔍 Extracting content from pages...")

    # Step 3: Get all valid pages and their content
    page_data = {url: get_page_content_and_links(url) for url in urls}

    # Filter out empty pages
    filtered_urls = [url for url, content in page_data.items() if content[0].strip()]
    filtered_corpus = [page_data[url][0] for url in filtered_urls]

    if len(filtered_corpus) < 2:
        st.error("❌ Not enough valid pages with content to compute similarity.")
        st.stop()

    # Step 4: Compute Similarity Scores for Content
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(filtered_corpus)
    similarity_matrix = X @ X.T  # TF-IDF cosine similarity computation

    # Step 5: Identify Internal Link Opportunities
    threshold = 0.15  # Adjust threshold for link relevance
    internal_link_suggestions = []

    for i, source_url in enumerate(filtered_urls):
        source_content, existing_links = page_data[source_url]

        for j, target_url in enumerate(filtered_urls):
            if i != j and similarity_matrix[i, j] > threshold and target_url not in existing_links:
                internal_link_suggestions.append((source_url, target_url, similarity_matrix[i, j]))

        # Update progress bar
        progress_bar.progress((i + 1) / len(filtered_urls))

    # Step 6: Display Results
    results_df = pd.DataFrame(internal_link_suggestions, columns=["Source Page", "Suggested Internal Link", "Relevance Score"])
    st.write("✅ Internal Link Suggestions:")
    st.dataframe(results_df)

    # Step 7: Downloadable CSV
    csv_data = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, "internal_link_suggestions.csv", "text/csv", key="download-csv")
