from docx import Document
from docx.text.run import Run
import streamlit as st

HEADING_STYLES = {
    "Title": "h1",
    "Heading 1": "h1",
    "Heading 2": "h2",
    "Heading 3": "h3",
    "Heading 4": "h4",
    "Heading 5": "h5",
    "Heading 6": "h6",
}

def format_run(run: Run) -> str:
    """Return HTML string for a styled text run."""
    text = run.text
    if not text:
        return ""

    if run.bold and run.italic:
        return f"<strong><em>{text}</em></strong>"
    elif run.bold:
        return f"<strong>{text}</strong>"
    elif run.italic:
        return f"<em>{text}</em>"
    else:
        return text

def format_paragraph(paragraph) -> str:
    """Handle inline formatting inside a paragraph."""
    return ''.join([format_run(run) for run in paragraph.runs])

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

        styled_text = format_paragraph(para)
        style = para.style.name

        # Headings
        if style in HEADING_STYLES:
            flush_list()
            tag = HEADING_STYLES[style]
            html.append(f"<{tag}>{styled_text}</{tag}>\n")
            continue

        # Lists
        if para._element.xpath('.//w:numPr'):
            list_type = "ol" if "Numbered" in style else "ul"
            in_list = True
            list_buffer.append(styled_text)
        else:
            flush_list()
            html.append(f"<p>{styled_text}</p>\n")

    flush_list()
    return "\n".join(html)


# --- Streamlit App ---
st.set_page_config(page_title="DOCX to HTML with Inline Styles", layout="wide")
st.title("📄 .docx to HTML Converter (with Bold/Italic)")

uploaded_file = st.file_uploader("Upload a .docx file", type=["docx"])

if uploaded_file:
    doc = Document(uploaded_file)
    html_output = docx_to_html(doc)

    st.markdown("### ✅ Cleaned HTML Output")
    st.code(html_output, language="html")

    st.download_button("⬇ Download HTML", html_output, file_name="converted.html", mime="text/html")
