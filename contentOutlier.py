import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import openai
import io

# Set up Streamlit UI
st.set_page_config(page_title="Content Outlier Detector", layout="wide")
st.title("🔍 Content Outlier Detector using OpenAI Embeddings")
st.markdown("""
This tool helps identify content that is semantically **off-topic** based on a user-defined theme (like "dog nutrition").

**How it works:**
1. Upload a Screaming Frog export with OpenAI embeddings
2. Enter your topic
3. We score and plot all articles based on semantic similarity
""")

# Upload CSV
uploaded_file = st.file_uploader("📄 Upload your Screaming Frog CSV (must include OpenAI embeddings)", type=["csv"])

# Input fields
topic = st.text_input("🎯 Enter your core topic (e.g. 'dog nutrition')")
openai_key = st.text_input("🔑 Enter your OpenAI API key", type="password")

# Sample template
with st.expander("📋 View required CSV format"):
    st.markdown("""
    The uploaded CSV must contain the following columns:
    - `Title 1` — The blog post title
    - `Address` — The blog post URL
    - `Text Embeddings (Open AI) 1` — The full OpenAI embedding (comma-separated vector)
    """)
    sample_df = pd.DataFrame({
        "Title 1": ["Example Title"],
        "Address": ["https://example.com/blog/example-title"],
        "Text Embeddings (Open AI) 1": ["0.001,0.123,..."]
    })
    st.dataframe(sample_df)

if uploaded_file and topic and openai_key:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {e}")
        st.stop()

    # Validate required columns
    required_columns = ["Title 1", "Address", "Text Embeddings (Open AI) 1"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"🚫 The uploaded CSV is missing required column(s): {', '.join(missing)}")
        st.stop()

    # Parse embeddings
    try:
        df["embedding_vector"] = df["Text Embeddings (Open AI) 1"].apply(lambda x: np.array([float(i) for i in x.split(",")]))
        embeddings = np.stack(df["embedding_vector"].values)
    except Exception as e:
        st.error(f"❌ Error parsing embeddings: {e}")
        st.stop()

    # Generate topic embedding
    try:
        client = openai.OpenAI(api_key=openai_key)
        response = client.embeddings.create(
            input=topic,
            model="text-embedding-3-small"
        )
        topic_embedding = np.array(response.data[0].embedding)
    except Exception as e:
        st.error(f"❌ Error generating topic embedding: {e}")
        st.stop()

    # Score similarity
    similarity_scores = cosine_similarity([topic_embedding], embeddings)[0]
    df["Similarity to Topic"] = similarity_scores

    # Show least aligned
    st.subheader("🚩 Least Aligned Articles")
    st.dataframe(df.sort_values("Similarity to Topic").head(10)[["Title 1", "Address", "Similarity to Topic"]])

    # PCA projection
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings)
    df["PCA_1"], df["PCA_2"] = reduced[:, 0], reduced[:, 1]

    # Plot
    st.subheader("🗺️ Visual Map of Content Similarity")
    fig, ax = plt.subplots()
    scatter = ax.scatter(df["PCA_1"], df["PCA_2"], c=df["Similarity to Topic"], cmap="viridis", alpha=0.8)
    plt.colorbar(scatter, label="Similarity to Topic")
    st.pyplot(fig)

    # Download CSV
    st.subheader("📥 Download Results")
    csv = df[["Title 1", "Address", "Similarity to Topic"]].sort_values("Similarity to Topic", ascending=False).to_csv(index=False)
    st.download_button("⬇️ Download Scored Articles as CSV", data=csv, file_name="scored_articles.csv", mime="text/csv")
