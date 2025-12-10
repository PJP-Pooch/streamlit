import re
import json
import streamlit as st
from bs4 import BeautifulSoup, Tag, NavigableString
import streamlit.components.v1 as components

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
    - Normalises list items so bullets paste cleanly into Contentful
    """
    if not isinstance(raw_html, str) or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, HTML_PARSER)

    # ---- IMAGES -> PLACEHOLDERS -------------------------------------------------
    for img in soup.find_all("img"):
        alt = img.get("alt") or ""
        src = img.get("src") or ""
        filename = src.split("/")[-1].split("?")[0] if src else ""

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

    # ---- LIST ITEMS: basic normalisation ----------------------------------------
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

    # ---- FIX: prevent whole-paragraph bold when only first sentence should be ----
    for p in soup.find_all("p"):
        element_children = [c for c in p.contents if isinstance(c, Tag)]
        if len(element_children) == 1 and element_children[0].name in ("strong", "b"):
            strong = element_children[0]
            full_text = strong.get_text()
            m = re.search(r'([.!?]["\']?\s+)', full_text)
            if m:
                split_idx = m.end()
                first = full_text[:split_idx]
                rest = full_text[split_idx:]
                strong.clear()
                strong.append(first)
                if rest.strip():
                    strong.insert_after(soup.new_string(rest))

    # ---- UNWRAP any nested <p> INSIDE LIST ITEMS --------------------------------
    for li in soup.find_all("li"):
        for p in list(li.find_all("p")):
            p.unwrap()

    # ---- FIX: Prevent bold + text being split (NBSP glue) -----------------------
    for li in soup.find_all("li"):
        children = list(li.children)

        for i, child in enumerate(children[:-1]):
            if isinstance(child, Tag) and child.name in ("b", "strong"):
                nxt = children[i + 1]

                if isinstance(nxt, NavigableString) and re.match(r"^[A-Za-z]", nxt.strip()):
                    new_txt = "\u00A0" + str(nxt)
                    nxt.replace_with(new_txt)

    # ---- MOVE PUNCTUATION AFTER <b>/<strong> INSIDE THE TAG (IN <li>) -----------
    for li in soup.find_all("li"):
        children = list(li.children)
        for i, child in enumerate(children[:-1]):
            if isinstance(child, Tag) and child.name in ("b", "strong"):
                nxt = children[i + 1]
                if isinstance(nxt, NavigableString):
                    txt = str(nxt)
                    txt_norm = txt.replace("\xa0", " ")
                    m = re.match(r"\s*([,;:.])(\s*)(.*)", txt_norm)
                    if m:
                        punct, spaces, rest = m.group(1), m.group(2), m.group(3)

                        if child.string is not None:
                            child.string.replace_with(str(child.string) + punct)
                        else:
                            child.append(punct)

                        new_txt = spaces + rest
                        if new_txt.strip() or new_txt != "":
                            nxt.replace_with(new_txt)
                        else:
                            nxt.extract()

    # ---- FINAL: wrap each <li> contents in a single <p> -------------------------
    # This gives: <li><p><strong>High in omega-3.</strong> Omega-3...</p></li>
    # which Contentful should treat as one bullet paragraph.
    for li in soup.find_all("li"):
        contents = list(li.contents)
        if not contents:
            continue

        # If it's already exactly one <p>, leave it
        if len(contents) == 1 and isinstance(contents[0], Tag) and contents[0].name == "p":
            continue

        p = soup.new_tag("p")
        for c in contents:
            p.append(c.extract())

        li.clear()
        li.append(p)

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
2. Click **Clean HTML** using the buttons at the top  
3. Click **Copy rendered content** above the preview  
4. Paste into your **Contentful Rich Text** field  

Bold, italics, underline, headings, lists, iframes & shortcodes will be preserved.  
Images show as `[IMAGE: ...]` so you can re-add them as Contentful assets.
"""
)

# Session state
if "cleaned_html" not in st.session_state:
    st.session_state.cleaned_html = ""
if "raw_html" not in st.session_state:
    st.session_state.raw_html = ""


def run_clean():
    st.session_state.cleaned_html = clean_html(st.session_state.raw_html)


def clear_all():
    st.session_state.raw_html = ""
    st.session_state.cleaned_html = ""


# ---- TOP ACTION BUTTONS (stacked vertically, left-aligned) ---------------------
btn_col, _ = st.columns([0.3, 0.7])
with btn_col:
    st.button("🧹 Clear input & output", on_click=clear_all, use_container_width=True)
    st.button("🔄 Clean HTML", on_click=run_clean, use_container_width=True)


# ---- LAYOUT: INPUT (LEFT) & PREVIEW (RIGHT) ------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Raw Shopify HTML")

    st.text_area(
        "Paste HTML here",
        key="raw_html",
        height=550,
        placeholder="Paste the blog HTML / DOM snippet from Shopify…",
    )

with col2:
    st.subheader("2️⃣ Cleaned preview (rendered)")

    if st.session_state.cleaned_html:
        # Copy button with nicer styling
        copy_button_html = f"""
        <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem;">
          <button id="copy-rendered-btn"
                  style="
                    padding:0.4rem 0.8rem;
                    border-radius:6px;
                    border:1px solid #d0d0d0;
                    background-color:#f5f5f5;
                    font-size:0.9rem;
                    cursor:pointer;
                  ">
            📋 Copy rendered content
          </button>
          <span id="copy-status" style="font-size:0.85rem; color:#555;"></span>
        </div>
        <script>
        const htmlContent = {json.dumps(st.session_state.cleaned_html)};
        const btn = document.getElementById('copy-rendered-btn');
        const status = document.getElementById('copy-status');

        if (btn) {{
          btn.addEventListener('click', async () => {{
            try {{
              if (navigator.clipboard && window.ClipboardItem) {{
                const blob = new Blob([htmlContent], {{ type: "text/html" }});
                const item = new ClipboardItem({{"text/html": blob}});
                await navigator.clipboard.write([item]);
              }} else {{
                await navigator.clipboard.writeText(htmlContent);
              }}
              btn.style.backgroundColor = "#e6ffed";
              btn.style.borderColor = "#34c759";
              status.textContent = "Copied to clipboard";
              status.style.color = "#555";
              setTimeout(() => {{
                btn.style.backgroundColor = "#f5f5f5";
                btn.style.borderColor = "#d0d0d0";
                status.textContent = "";
              }}, 1500);
            }} catch (err) {{
              console.error(err);
              status.textContent = "Copy failed, please use Ctrl+A / Ctrl+C in the preview.";
              status.style.color = "#d00";
            }}
          }});
        }}
        </script>
        """
        components.html(copy_button_html, height=60)

        st.caption(
            "This is the cleaned HTML rendered as rich text so you can visually check headings, "
            "lists, links, iframes, and shortcodes.\n\n"
            "Use **Copy rendered content** above. If that fails, click here and press **Ctrl+A**, then **Ctrl+C**."
        )

        st.markdown(
            f'<div id="clean-preview">{st.session_state.cleaned_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Paste HTML on the left and click **Clean HTML** at the top to see the result here.")
