import torch
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

# Function to get the embedding of a text using BERT
def get_embedding(text, model, tokenizer):
    inputs = tokenizer(text, return_tensors='pt')
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().numpy()

# Main function for the Streamlit app
def main():
    st.title("Sentence and Keyword Similarity with BERT")
    
    # Text input fields for sentence and keyword
    sentence = st.text_input("Sentence:")
    keyword = st.text_input("Keyword:")
    
    if sentence and keyword:
        # Load tokenizer and model
        tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        model = BertModel.from_pretrained('bert-base-uncased')

        # Get embeddings for sentence and keyword
        sentence_embedding = get_embedding(sentence, model, tokenizer)
        keyword_embedding = get_embedding(keyword, model, tokenizer)

        # Calculate cosine similarity
        similarity_score = cosine_similarity(sentence_embedding, keyword_embedding)[0][0]

        # Truncate embeddings for display
        sentence_embedding_truncated = sentence_embedding[0][:10]
        keyword_embedding_truncated = keyword_embedding[0][:10]

        # Display results
        st.write(f"**Sentence:** {sentence}")
        st.write(f"**Embedding:** {sentence_embedding_truncated.tolist()} ...")
        st.write(f"**Keyword:** {keyword}")
        st.write(f"**Embedding:** {keyword_embedding_truncated.tolist()} ...")
        st.write(f"**Similarity Score:** {similarity_score:.4f}")

# Run the app
if __name__ == "__main__":
    main()
