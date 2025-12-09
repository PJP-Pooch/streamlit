import re
import html2text
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
    """Clean Shopify-style HTML for Contentful use."""
    if not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, HTML_PARSER)

    # 0) Remove images entirely (you'll re-add key ones manually in Contentful)
    for img in soup.find_all("img"):
        img.decompose()

    # 1) Remove span wrappers but keep their content
    for span in soup.find_all("span"):
        span.unwrap()

    # 2) Replace <br> with a space so they don't fragment sentences
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

    # 6) Strip non-essential attributes (keep href/src if they exist)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr not in ("href", "src"):
                del tag.attrs[attr]

    # Return just the inner HTML of the body if present, otherwise full soup
    if soup.body:
        return soup.body.decode_contents()
    return str(soup)

def html_to_markdown(clean_html: str) -> str:
    """Convert cleaned HTML to Markdown suitable for pasting into Contentful Rich Text."""
    if not clean_html.strip():
        return ""

    h = html2text.HTML2Text()
    h.ignore_links = False   # keep [text](url)
    h.ignore_images = True   # we've already removed images
    h.body_width = 0         # don't hard-wrap lines

    md = h.handle(clean_html)
    return md.strip()

# ---------- STREAMLIT UI ----------

st.set_page_config(page_title="Shopify → Contentful Cleaner", layout="wide")

st.title("Shopify → Contentful Blog Cleaner")
st.write(
    "Paste your **Shopify blog HTML** on the left. "
    "You'll get **cleaned HTML** in the middle and **Contentful-ready Markdown** on the right."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1️⃣ Raw Shopify HTML")
    raw_html = st.text_area(
        "Paste HTML here",
        height=600,
        placeholder="Paste the blog body HTML from Shopify (or your DOM snippet)…",
    )

with col2:
    st.subheader("2️⃣ Cleaned HTML")
    if raw_html.strip():
        cleaned = clean_html(raw_html)
        st.caption(
            "This is cleaned HTML (no span soup / empty paragraphs / nested <p> inside <li>). "
            "You *can* use this directly if needed, but usually you'll want the Markdown in column 3."
        )
        st.code(cleaned, language="html")
    else:
        cleaned = ""
        st.info("Paste some HTML in column 1 to see cleaned HTML here.")

with col3:
    st.subheader("3️⃣ Contentful-ready Markdown")
    if cleaned.strip():
        markdown = html_to_markdown(cleaned)
        st.caption(
            "Copy this and paste it into your **Contentful Rich Text** field. "
            "Contentful will convert headings, lists, and links into proper Rich Text nodes. "
            "Shortcodes like `[table=…]` and `[highlight-block=…]` are preserved."
        )
        st.code(markdown, language="markdown")

        # Small helper: show character count for sanity
        st.write(f"Character count: **{len(markdown)}**")
    else:
        st.info("Once there's cleaned HTML in column 2, Markdown will appear here.")
