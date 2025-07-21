from docx import Document
import streamlit as st

# Define styles that map to headings
HEADING_STYLES = {
    "Title": "h1",
    "Heading 1": "h1",
    "Heading 2": "h2",
    "Heading 3": "h3",
    "Heading 4": "h4",
    "Heading 5": "h5",
    "Heading 6": "h6",
}

def docx_to_html(doc):
    html = []
    in_list = False
    list_type = None
    list_buffer = []

    def flush_list():
        nonlocal in_list, list_buffer, list_type
        if list_buffer:
            tag = "ul" if list_type == "ul" else "ol"
            html.append(f"<{tag}>")
            for item in list_buffer:
                html.append(f"<li>{item}</li>")
            html.append(f"</{tag}>")
        in_list = False
        list_buffer = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            flush_list()
            continue

        style = para.style.name

        # Check for heading
        if style in HEADING_STYLES:
            flush_list()
            tag = HEADING_STYLES[style]
            html.append(f"<{tag}>{text}</{tag}>")
            continue

        # Check for bullets and numbering
        if para._element.xpath('.//w:numPr'):
            list_type = "ol" if "Numbered" in style else "ul"
            in_list = True
            list_buffer.append(text)
        else:
            flush_list()
            html.append(f"<p>{text}</p>")

    flush_list()
    return "\n".join(html)

# Streamlit interface
st.set_page_config(page_title="DOCX to HTML Converter", layout="wide")
st.title("📄 Convert .docx to Clean HTML")

uploaded_file = st.file_uploader("Upload a .docx file", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    html_output = docx_to_html(doc)

    st.markdown("### ✅ Cleaned HTML Output")
    st.code(html_output, language="html")

    st.download_button("⬇ Download HTML", html_output, file_name="converted.html", mime="text/html")
