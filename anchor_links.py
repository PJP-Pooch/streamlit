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

            soup = BeautifulSoup(response.tex
