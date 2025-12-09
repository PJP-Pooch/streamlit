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
    """
    Clean Shopify-style HTML for pasting into Contentful Rich Text.

    - Preserves <strong>/<b>, <em>/<i>, <u>
    - Converts styled spans (font-weight / font-style / underline) into semantic tags
    - Keeps iframes (e.g. YouTube / Vimeo)
    - Replaces <img> with a readable [IMAGE: ...] placeholder
    - Preserves shortcodes like [table=...], [highlight-block=...], [cta=...]
    """
    if not isinstance(raw_html, str) or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, HTML_PARSER)

    # ---- IMAGES -> PLACEHOLDERS -------------------------------------------------
    for img in soup.find_all("img"):
        alt = img.get("alt") or ""
        src = img.get("src") or ""
        filename = ""
        if src:
            filename = src.split("/")[-1].split("?")[0]

        parts = [p for p in [alt.strip(), filename.strip()] if p]
        label = " / ".join(parts) if parts else "IMAGE"
        placeholder_text = f"[IMAGE: {label}]"

        img.replace_with(soup.new_string(placeholder_text))

    # ---- SPANS -> STRONG / EM / U OR PLAIN --------------------------------------
    for span in list(soup.find_all("span")):
        style = span.get("style", "").lower()

        if "font-weight" in style and ("700" in style or "bold" in style):
            span.name = "strong"
            span.attrs.pop("style", None)
        elif "font-style" in style and "italic" in style:
            span.name = "em"
            span.attrs.pop("style", None)
        elif "text-decoration" in style and "underline" in style:
            span.name = "u"
            span.attrs.pop("style", None)
        else:
            span.unwrap()

    # ---- <br> -> SPACE ----------------------------------------------------------
    for br in soup.find_all("br"):
        br.replace_with(" ")

    # ---- PARAGRAPHS -------------------------------------------------------------
    for p in list(soup.find_all("p")):
        text = p.get_text(" ", strip=True)

        if is_empty_or_nbsp(text):
            p.decompose()
            continue

        # Shortcodes: keep as plain one-line text
        if any(pattern in text for pattern in SHORTCODE_PATTERNS):
            p.clear()
            p.string = re.sub(r"\s+", " ", text)
            continue

        inner_html = p.decode_contents()
        normalized_inner = re.sub(r"\s+", " ", inner_html).strip()
        new_children = BeautifulSoup(normalized_inner, HTML_PARSER)

        p.clear()
        if new_children.body:
            for child in list(new_children.body.contents):
                p.append(child)
        else:
            for child in list(new_children.contents):
                p.append(child)

    # ---- LIST ITEMS -------------------------------------------------------------
    for li in list(soup.find_all("li")):
        text = li.get_text(" ", strip=True)
        if is_empty_or_nbsp(text):
            li.decompose()
            continue

        # unwrap single <p> child if that's the structure
        children = [c for c in li.contents if hasattr(c, "name")]
        if len(children) == 1 and children[0].name == "p":
            children[0].unwrap()

        inner_html = li.decode_contents()
        normalized_inner = re.sub(r"\s+", " ", inner_html).strip()
        new_children = BeautifulSoup(normalized_inner, HTML_PARSER)

        li.clear()
        if new_children.body:
            for child in list(new_children.body.contents):
                li.append(child)
        else:
            for child in list(new_children.contents):
                li.append(child)

    # ---- HEADINGS ---------------------------------------------------------------
    for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for h in list(soup.find_all(level)):
            text = h.get_text(" ", strip=True)
            if is_empty_or_nbsp(text):
                h.decompose()
                continue

            inner_html = h.decode_contents()
            normalized_inner = re.sub(r"\s+", " ", inner_html).strip()
            new_children = BeautifulSoup(normalized_inner, HTML_PARSER)

            h.clear()
            if new_children.body:
                for child in list(new_children.body.contents):
                    h.append(child)
            else:
                for child in list(new_children.contents):
                    h.append(child)

    # ---- ATTRIBUTES (keep link + iframe attrs) ----------------------------------
    iframe_safe_attrs = {
        "src",
        "width",
        "height",
        "allow",
        "allowfullscreen",
        "frameborder",
        "title",
        "loading",
        "referrerpolicy",
    }

    for tag in soup.find_all(True):
        if tag.name == "iframe":
            for attr in list(tag.attrs.keys()):
                if attr not in iframe_safe_attrs:
                    del tag.attrs[attr]
            continue

        for attr in list(tag.attrs.keys()):
            if attr not in ("href", "src"):
                del tag.attrs[attr]

    if soup.body:
        return soup.body.decode_contents()
    return str(soup)


# ---------------- STREAMLIT UI ----------------

st.set_page_config(page_title="Shopify → Contentful Cleaner", layout="wide")

st.title("Shopify → Contentful Blog Cleaner")

st.markdown(
    """
1. Paste the **Shopify blog HTML** on the left  
2. Click **Clean HTML**  
3. Click **Copy cleaned HTML** on the right, then paste into your **Contentful Rich Text** field  

Bold, italics, underline, headings, lists, iframes & shortcodes will be preserved.  
Images show as `[IMAGE: ...]` so you can re-add them as Contentful assets.
"""
)

if "cleaned_html" not in st.session_state:
    st.session_state.cleaned_html = ""

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Raw Shopify HTML")

    raw_html = st.text_area(
        "Paste HTML here",
        key="raw_html",
        height=550,
        placeholder="Paste the blog HTML / DOM snippet from Shopify…",
    )

    if st.button("Clean HTML"):
        st.session_state.cleaned_html = clean_html(st.session_state.raw_html)

with col2:
    st.subheader("2️⃣ Cleaned preview & copy")

    if st.session_state.cleaned_html:
        preview_id = "clean-preview"

        # Copy button RIGHT AT THE TOP of the preview column
        copy_button_html = f"""
        <button
            style="
                background-color:#4F46E5;
                color:white;
                border:none;
                padding:0.5rem 1rem;
                border-radius:0.5rem;
                cursor:pointer;
                margin-bottom:0.75rem;
            "
            onclick="
                var el = document.getElementById('{preview_id}');
                if (!el) return;
                var html = el.innerHTML;
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(html).then(function() {{
                        alert('Clean HTML copied to clipboard!');
                    }}).catch(function(err) {{
                        console.error(err);
                        alert('Could not copy automatically. Please select the text and copy manually.');
                    }});
                }} else {{
                    var range = document.createRange();
                    range.selectNodeContents(el);
                    var sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                    document.execCommand('copy');
                    alert('Clean HTML copied to clipboard!');
                }}
            "
        >
            Copy cleaned HTML
        </button>
        """

        # Render the copy button (as actual HTML, not text!)
        st.markdown(copy_button_html, unsafe_allow_html=True)

        st.caption(
            "Below is the cleaned HTML rendered as rich text. "
            "If the copy button doesn’t work in your browser, "
            "click in this area, press **Ctrl+A** then **Ctrl+C**, and paste into Contentful."
        )

        # The preview itself
        st.markdown(
            f'<div id="{preview_id}">{st.session_state.cleaned_html}</div>',
            unsafe_allow_html=True,
        )

    else:
        st.info("Paste HTML on the left and click **Clean HTML** to see the result here.")
