import streamlit as st
from bs4 import BeautifulSoup
import re

def clean_google_docs_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    allowed_tags = {"p", "strong", "b", "em", "i", "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "h6", "img", "br"}

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in ["href", "src", "alt"]}

    cleaned_html = soup.decode(formatter="html")
    cleaned_html = re.sub(r"[“”]", '"', cleaned_html)
    cleaned_html = re.sub(r"[‘’]", "'", cleaned_html)
    cleaned_html = re.sub(r"–|—", "-", cleaned_html)
    cleaned_html = re.sub(r"\s+\n", "\n", cleaned_html)
    cleaned_html = re.sub(r"\n{3,}", "\n\n", cleaned_html)
    cleaned_html = cleaned_html.strip()

    return cleaned_html

st.set_page_config(page_title="Google Docs HTML Cleaner", layout="wide")
st.title("🧹 Google Docs to Shopify HTML Cleaner")

input_html = st.text_area("Paste your raw HTML from Google Docs here:", height=300)

if st.button("Clean HTML"):
    if input_html:
        cleaned = clean_google_docs_html(input_html)
        st.text_area("Cleaned HTML:", value=cleaned, height=300)
        st.download_button("Download Cleaned HTML", cleaned, file_name="cleaned_output.html", mime="text/html")
    else:
        st.warning("Please paste some HTML above to clean.")
