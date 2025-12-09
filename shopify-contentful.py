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

    # 0) Preserve iframes (YouTube/Vimeo) exactly as they are
    #    (we don't touch them anywhere else, just avoid removing attributes unnecessarily)
    #    Nothing to do here explicitly, just DON'T decompose or unwrap them later.

    # 1) Replace <img> tags with readable placeholders so you can re-add them in Contentful
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

    # 2) Handle <span>:
    #    - bold:   font-weight:700/bold  -> <strong>
    #    - italic: font-style:italic     -> <em>
    #    - underline: text-decoration:underline -> <u>
    #    - everything else: unwrap to plain text
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

    # 3) Replace <br> with a single space so they don't fragment sentences
    for br in soup.find_all("br"):
        br.replace_with(" ")

    # 4) Clean paragraphs but DO NOT destroy nested markup (<strong>, <em>, <u>, links etc.)
    for p in list(soup.find_all("p")):
        text = p.get_text(" ", strip=True)

        # Remove empty paragraphs
        if is_empty_or_nbsp(text):
            p.decompose()
            continue

        # Shortcode paragraphs: just normalise whitespace and keep as plain text
        if any(pattern in text for pattern in SHORTCODE_PATTERNS):
            p.clear()
            p.string = re.sub(r"\s+", " ", text)
            continue

        # For normal paragraphs we *don't* clear children, to keep <strong>/<em>/<u>/links
        # We only collapse excessive whitespace between words in text nodes.
        # Easiest safe approach: normalise the innerHTML string, then re-parse it.
        inner_html = p.decode_contents()
        normalized_inner = re.sub(r"\s+", " ", inner_html).strip()
        new_children = BeautifulSoup(normalized_inner, HTML_PARSER)

        p.clear()
        # new_children.body may exist if parser wraps; otherwise use new_children directly
        if new_children.body:
            for child in list(new_children.body.contents):
                p.append(child)
        else:
            for child in list(new_children.contents):
                p.append(child)

    # 5) Normalise list items:
    #    - unwrap <p> inside <li>
    #    - keep inline formatting (<strong>, <em>, <u>, links)
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

    # 6) Headings: just normalise whitespace but keep tags & inline markup
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

    # 7) Strip non-essential attributes everywhere EXCEPT:
    #    - href (links)
    #    - src  (for iframes, videos, etc.)
    #    - allow / allowfullscreen / frameborder etc for iframes
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
        # leave iframe attributes mostly intact
        if tag.name == "iframe":
            for attr in list(tag.attrs.keys()):
                if attr not in iframe_safe_attrs:
                    del tag.attrs[attr]
            continue

        for attr in list(tag.attrs.keys()):
            if attr not in ("href", "src"):
                del tag.attrs[attr]

    # Return the inner HTML of <body> if present; else the whole soup
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
3. Use the **Copy** button or select the preview on the right and paste into your **Contentful Rich Text** field  
   (bold, italics, underline, lists, headings, iframes & shortcodes will be preserved; images show as `[IMAGE: ...]`).
"""
)

# state for cleaned HTML so it survives reruns
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
    st.subheader("2️⃣ Cleaned preview (copy into Contentful)")

    if st.session_state.cleaned_html:
        st.caption(
            "This is the cleaned HTML rendered as rich text.\n\n"
            "You can either:\n"
            "- Click **Copy cleaned HTML** below, then paste into the Contentful Rich Text field, or\n"
            "- Click anywhere in this preview, press **Ctrl+A** then **Ctrl+C**, and paste."
        )

        # Preview wrapped in a div with an id so JS can grab it
        preview_id = "clean-preview"

        st.markdown(
            f'<div id="{preview_id}">{st.session_state.cleaned_html}</div>',
            unsafe_allow_html=True,
        )

        # Copy button using JS – copies the innerHTML of the preview div
        copy_button_js = f"""
        <button
            onclick="
                const el = document.getElementById('{preview_id}');
                if (!el) return;
                const html = el.innerHTML;
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(html).then(() => {{
                        alert('Clean HTML copied to clipboard!');
                    }}).catch(err => {{
                        console.error(err);
                        alert('Could not copy automatically. Please select the text and copy manually.');
                    }});
                }} else {{
                    // Fallback for older browsers
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    const sel = window.getSelection();
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

        st.markdown(copy_button_js, unsafe_allow_html=True)
    else:
        st.info("Paste HTML on the left and click **Clean HTML** to see the result here.")
