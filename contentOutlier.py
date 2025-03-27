import streamlit as st
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import openai
import matplotlib.pyplot as plt

openai_key = st.text_input("🔑 Enter your OpenAI API key", type="password")

if openai_key:
    openai.api_key = openai_key

st.title("Content Outlier Detector using OpenAI Embeddings")

uploaded_file = st.file_uploader("Upload Screaming Frog CSV with Embeddings")
topic = st.text_input("Enter your core topic (e.g. 'dog nutrition')")

if uploaded_file and topic:
    df = pd.read_csv(uploaded_file)
    df["embedding_vector"] = df["Text Embeddings (Open AI) 1"].apply(lambda x: np.array([float(i) for i in x.split(",")]))
    embeddings = np.stack(df["embedding_vector"].values)

    topic_embedding = openai.Embedding.create(input=[topic], model="text-embedding-3-small")["data"][0]["embedding"]
    topic_embedding = np.array(topic_embedding)

    similarity_scores = cosine_similarity([topic_embedding], embeddings)[0]
    df["Similarity to Topic"] = similarity_scores

    # Show least aligned
    st.subheader("Least Aligned Articles")
    st.dataframe(df.sort_values("Similarity to Topic").head(10)[["Title 1", "Address", "Similarity to Topic"]])

    # Plot
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings)
    df["PCA_1"], df["PCA_2"] = reduced[:, 0], reduced[:, 1]
    fig, ax = plt.subplots()
    scatter = ax.scatter(df["PCA_1"], df["PCA_2"], c=df["Similarity to Topic"], cmap="viridis")
    fig.colorbar(scatter, label="Similarity to Topic")
    st.pyplot(fig)

    # Download
    st.download_button("Download Scored CSV", df.to_csv(index=False), "scored_articles.csv")
