import streamlit as st
import re

st.set_page_config(page_title="Google Docs to HTML Cleaner", layout="wide")
st.title("🧹 Google Docs to HTML Cleaner")

def plain_text_to_html(raw_text):
    lines = raw_text.splitlines()
    output = []
    in_list = False
    list_type = None
    list_items = []

    def flush_list():
        nonlocal list_items, in_list, list_type
        if list_items:
            tag = "ul" if list_type == "ul" else "ol"
            output.append(f"<{tag}>")
            for item in list_items:
                output.append(f"<li>{item}</li>")
            output.append(f"</{tag}>")
            list_items = []
            in_list = False
            list_type = None

    for line in lines:
        line = line.strip()

        if not line:
            flush_list()
            continue

        if line.lower().startswith("title:"):
            flush_list()
            title = line.split(":", 1)[1].strip()
            output.append(f"<h1>{title}</h1>")
            continue
        elif line.lower().startswith("meta title:") or line.lower().startswith("meta description:") or line.lower().startswith("status:"):
            flush_list()
            output.append(f"<!-- {line.strip()} -->")
            continue
        elif re.match(r"^heading \d:", line.lower()):
            flush_list()
            match = re.match(r"^heading (\d):(.+)", line, re.IGNORECASE)
            if match:
                level = match.group(1)
                text = match.group(2).strip()
                output.append(f"<h{level}>{text}</h{level}>")
            continue
        elif line == "[FIND OUT MORE]":
            flush_list()
            output.append('<p><a href="#" class="cta">FIND OUT MORE</a></p>')
            continue
        elif "[Related article:" in line:
            flush_list()
            related = re.findall(r"\[Related article: (.*?)\]", line)
            if related:
                output.append(f'<p><em>Related article: {related[0]}</em></p>')
            continue
        elif "[product-carousel" in line:
            flush_list()
            prod = re.findall(r"\[product-carousel (.*?)\]", line)
            if prod:
                output.append(f'<div class="product-carousel" data-id="{prod[0]}"></div>')
            continue

        if re.match(r"^[-*•]\s+", line):
            item = re.sub(r"^[-*•]\s+", "", line)
            if not in_list:
                flush_list()
                in_list = True
                list_type = "ul"
            list_items.append(item)
            continue
        elif re.match(r"^\d+\.\s+", line):
            item = re.sub(r"^\d+\.\s+", "", line)
            if not in_list:
                flush_list()
                in_list = True
                list_type = "ol"
            list_items.append(item)
            continue
        else:
            flush_list()
            output.append(f"<p>{line}</p>")

    flush_list()
    return "\n".join(output)

# --- UI ---
uploaded_file = st.file_uploader("📄 Upload a .txt file from Google Docs", type=["txt"])
pasted_text = st.text_area("Or paste text copied from Google Docs here:", height=300)

if uploaded_file:
    raw_text = uploaded_file.read().decode("utf-8")
elif pasted_text:
    raw_text = pasted_text
else:
    raw_text = ""

if raw_text:
    cleaned_html = plain_text_to_html(raw_text)
    st.markdown("### ✅ Cleaned HTML Preview")
    st.code(cleaned_html, language="html")

    st.download_button("⬇ Download HTML", cleaned_html, file_name="cleaned_output.html", mime="text/html")
