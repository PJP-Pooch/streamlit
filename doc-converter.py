import streamlit as st
from docx import Document

HEADING_STYLES = {
    "Title": "h1",
    "Heading 1": "h1",
    "Heading 2": "h2",
    "Heading 3": "h3",
    "Heading 4": "h4",
    "Heading 5": "h5",
    "Heading 6": "h6",
}

def format_paragraph(paragraph, strip_bold=False):
    """Split paragraph into chunks on <w:br> (manual line breaks)."""
    chunks = []
    current = []

    for run in paragraph.runs:
        text = run.text or ""
        xml = run._element

        if not text and not xml.xpath(".//w:br"):
            continue

        # Format inline styles
        if strip_bold and run.bold and run.italic:
            part = f"<em>{text}</em>"
        elif strip_bold and run.bold:
            part = text
        elif run.bold and run.italic:
            part = f"<strong><em>{text}</em></strong>"
        elif run.bold:
            part = f"<strong>{text}</strong>"
        elif run.italic:
            part = f"<em>{text}</em>"
        else:
            part = text

        current.append(part)

        # Detect line break and start new chunk
        if xml.xpath(".//w:br"):
            chunks.append(''.join(current).strip())
            current = []

    if current:
        chunks.append(''.join(current).strip())

    return chunks

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
                html.append(f"  <li>{item}</li>")
            html.append(f"</{tag}>\n")
        in_list = False
        list_buffer = []

    for para in doc.paragraphs:
        if not para.text.strip():
            flush_list()
            continue

        style = para.style.name
        is_heading = style in HEADING_STYLES
        strip_bold = is_heading
        chunks = format_paragraph(para, strip_bold=strip_bold)

        if is_heading:
            flush_list()
            tag = HEADING_STYLES[style]
            for chunk in chunks:
                html.append(f"<{tag}>{chunk}</{tag}>\n")
            continue

        if para._element.xpath('.//w:numPr'):
            list_type = "ol" if "Numbered" in style else "ul"
            in_list = True
            list_buffer.extend(chunks)
        else:
            flush_list()
            for chunk in chunks:
                html.append(f"<p>{chunk}</p>\n")

    flush_list()
    return '\n'.join(html)

# --- Streamlit App ---
st.set_page_config(page_title="DOCX to Clean HTML", layout="wide")
st.title("📄 .docx to Clean HTML Converter")

uploaded_file = st.file_uploader("Upload a .docx file", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    html_output = docx_to_html(doc)

    st.markdown("### ✅ Cleaned HTML Output")
    st.code(html_output, language="html")

    st.download_button("⬇ Download HTML", html_output, file_name="converted.html", mime="text/html")
