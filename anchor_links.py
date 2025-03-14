import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import nltk

# Download NLTK stopwords
nltk.download('stopwords')
from nltk.corpus import stopwords

# Streamlit App Title
st.title("🔗 Internal Link Finder (With Smart Anchor Text)")

# User Input: XML Sitemap URL
sitemap_url = st.text_input("Enter your XML Sitemap URL", "")

# Adjustable slider for threshold
threshold = st.slider("Set Link Relevance Threshold", 0.05, 0.40, 0.15, 0.01)
st.write(f"🔧 Current threshold: **{threshold:.2f}** (Lower = More Links, Higher = Stricter)")

# Button to start processing
if st.button("Find Internal Link Opportunities") and sitemap_url:

    st.write("🔍 Fetching URLs from the sitemap...")

    # Step 1: Fetch all URLs from XML Sitemap
    def get_sitemap_urls(sitemap_url):
        """Fetch and parse URLs from XML sitemap, filtering out non-HTML pages."""
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.content, "xml")
        urls = [loc.text for loc in soup.find_all("loc")]

        # Filter out image URLs (Shopify CDN, PNG, JPG, etc.)
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
    internal_link_suggestions = []

    # Function to suggest **contextually relevant anchor text**
    def suggest_anchor_text(source_content, target_content):
        """Extracts a relevant keyword phrase that overlaps between the source and target content."""
        combined_texts = [source_content, target_content]
        tfidf = TfidfVectorizer(stop_words=stopwords.words("english"), ngram_range=(1, 3))
        tfidf_matrix = tfidf.fit_transform(combined_texts)
        feature_names = tfidf.get_feature_names_out()

        # Get top-scoring keywords from source and target content
        source_tfidf_scores = tfidf_matrix[0].toarray()[0]
        target_tfidf_scores = tfidf_matrix[1].toarray()[0]

        # Rank words based on importance
        source_top_keywords = {feature_names[i]: source_tfidf_scores[i] for i in source_tfidf_scores.argsort()[::-1]}
        target_top_keywords = {feature_names[i]: target_tfidf_scores[i] for i in target_tfidf_scores.argsort()[::-1]}

        # Find overlap between top words from both pages
        overlapping_keywords = [kw for kw in source_top_keywords if kw in target_top_keywords]

        # Select the best phrase as anchor text
        if overlapping_keywords:
            return overlapping_keywords[0].capitalize()  # Choose first meaningful match

        # If no match, fall back to highest-ranked term from target page
        return list(target_top_keywords.keys())[0].capitalize()

    for i, source_url in enumerate(filtered_urls):
        source_content, existing_links = page_data[source_url]

        for j, target_url in enumerate(filtered_urls):
            if i != j and similarity_matrix[i, j] > threshold and target_url not in existing_links:
                suggested_anchor = suggest_anchor_text(source_content, page_data[target_url][0])
                internal_link_suggestions.append((source_url, target_url, suggested_anchor, similarity_matrix[i, j]))

        # Update progress bar
        progress_bar.progress((i + 1) / len(filtered_urls))

    # Step 6: Display Results
    results_df = pd.DataFrame(internal_link_suggestions, columns=["Source Page", "Suggested Internal Link", "Suggested Anchor Text", "Relevance Score"])
    st.write("✅ Internal Link Suggestions with Contextually Relevant Anchor Text:")
    st.dataframe(results_df)

    # Step 7: Downloadable CSV
    csv_data = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, "internal_link_suggestions.csv", "text/csv", key="download-csv")
