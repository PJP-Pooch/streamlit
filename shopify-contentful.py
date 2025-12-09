import re
import streamlit as st
from bs4 import BeautifulSoup

HTML_PARSER = "html5lib"
SHORTCODE_PATTERNS = ("[table=", "[highlight-block=", "[cta=")

def is_empty_or_nbsp(text: str) -> bool:
    if text is None:
        return True
    cleaned = text.replace("\xa0", " ").strip()
    return cleaned == ""

def clean_html(raw_html: str) -> str:
    """Clean Shopify-style HTML for pasting into Contentful Rich Text."""
    if not isinstance(raw_html, str) or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, HTML_PARSER)

    # 0) Drop images (you’ll re-add key ones in Contentful)
    for img in soup.find_all("img"):
        img.decompose()

    # 1) Remove span wrappers but keep their content
    for span in soup.find_all("span"):
        span.unwrap()

    # 2) Replace <br> with spaces so they don't fragment sentences
    for br in soup.find_all("br"):
        br.replace_with(" ")

    # 3) Normalise paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)

        # Keep shortcode paragraphs as clean one-liners
        if any(pattern in text for pattern in SHORTCODE_PATTERNS):
            text = re.sub(r"\s+", " ", text)
            p.clear()
            p.string = text
            continue

        # Drop empty/whitespace-only paragraphs
        if is_empty_or_nbsp(text):
            p.decompose()
            continue

        text = re.sub(r"\s+", " ", text)
        p.clear()
        p.string = text

    # 4) Normalise list items (<ul><li><p>Text</p></li> -> <li>Text</li>)
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if is_empty_or_nbsp(text):
            li.decompose()
            continue
        text = re.sub(r"\s+", " ", text)
        li.clear()
        li.string = text

    # 5) Clean headings
    for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for h in soup.find_all(level):
            text = h.get_text(" ", strip=True)
            if is_empty_or_nbsp(text):
                h.decompose()
                continue
            text = re.sub(r"\s+", " ", text)
            h.clear()
            h.string = text

    # 6) Strip non-essential attributes (keep href/src)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr not in ("href", "src"):
                del tag.attrs[attr]

    # Return inner HTML of <body> if present, otherwise whole soup
    if soup.body:
        return soup.body.decode_contents()
    return str(soup)

# ---------------- STREAMLIT UI ----------------

st.set_page_config(page_title="Shopify → Contentful Cleaner", layout="wide")

st.title("Shopify → Contentful Blog Cleaner")
st.write(
    "Paste **Shopify blog HTML** on the left.\n\n"
    "Then **copy from the rendered preview in the middle** and paste into "
    "your **Contentful Rich Text** field. The right column just shows the "
    "cleaned HTML source f
