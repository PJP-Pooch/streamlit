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

        # Handle hyperlinks
        hyperlink_field = xml.xpath(".//w:hyperlink")
        if hyperlink_field:
            # Not supported well in python-docx yet
            pass

        # Format inline styles
        if strip_bold and run.bold:
            bold = False
        else:
            bold = run.bold

        part = text
        if bold and run.italic:
            part = f"<strong><em>{text}</em></strong>"
        elif bold:
            part = f"<strong>{text}</strong>"
        elif run.italic:
            part = f"<em>{text}</em>"
        elif run.underline:
            part = f"<u>{text}</u>"

        current.append(part)

        if xml.xpath(".//w:br"):
            chunks.append(''.join(current).strip())
            current = []

    if current:
        chunks.append(''.join(current).strip())

    return chunks

def docx_to_html(doc):
    html = []
    markdown = []
    in_list = False
    list_type = None
    list_buffer = []
    md_list_buffer = []

    def flush_list():
        nonlocal in_list, list_buffer, list_type, md_list_buffer
        if list_buffer:
            tag = "ul" if list_type == "ul" else "ol"
            html.append(f"<{tag}>")
            for item in list_buffer:
                html.append(f"  <li>{item}</li>")
            html.append(f"</{tag}>\n")
        if md_list_buffer:
            markdown.extend(md_list_buffer)
        in_list = False
        list_buffer = []
        md_list_buffer = []

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
                markdown.append(f"{'#' * int(tag[1])} {chunk}")
            continue

        if para._element.xpath('.//w:numPr'):
            list_type = "ol" if "Numbered" in style else "ul"
            in_list = True
            list_buffer.extend(chunks)
            prefix = "1." if list_type == "ol" else "-"
            md_list_buffer.extend([f"{prefix} {c}" for c in chunks])
        else:
            flush_list()
            for chunk in chunks:
                html.append(f"<p>{chunk}</p>\n")
                markdown.append(chunk)

    flush_list()
    return '\n'.join(html), '\n'.join(markdown)

# --- Streamlit App ---
st.set_page_config(page_title="DOCX to Clean HTML", layout="wide")
st.title("📄 .docx to Clean HTML + Markdown Converter")

uploaded_file = st.file_uploader("Upload a .docx file", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    html_output, md_output = docx_to_html(doc)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Cleaned HTML")
        st.code(html_output, language="html")
        st.download_button("⬇ Download HTML", html_output, file_name="converted.html", mime="text/html")

    with col2:
        st.markdown("### 📝 Markdown Output")
        st.code(md_output, language="markdown")
        st.download_button("⬇ Download Markdown", md_output, file_name="converted.md", mime="text/markdown")

    st.markdown("### 🌐 Live Preview")
    st.components.v1.html(f"""
    <div style='font-family: sans-serif; line-height: 1.6;'>{html_output}</div>
    """, height=600, scrolling=True)
