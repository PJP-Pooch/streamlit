import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.title("Bulk Image Quality Checker")

st.markdown("""
Upload a CSV of image URLs and we'll analyze each for:
- **Resolution** (width/height)
- **Blurriness** (using variance of Laplacian)

Images flagged as low resolution or blurry will be highlighted.
""")

uploaded_file = st.file_uploader("Upload CSV of image URLs", type=["csv"])

min_width = st.number_input("Minimum width (px)", value=800)
min_height = st.number_input("Minimum height (px)", value=800)
blur_threshold = st.slider("Blurriness threshold (lower = blurrier)", min_value=0, max_value=1000, value=100)


def fetch_image(url):
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content)).convert('RGB')
        width, height = img.size

        # Blurriness check
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

        return {
            "url": url,
            "width": width,
            "height": height,
            "blur_score": blur_score,
            "is_low_res": width < min_width or height < min_height,
            "is_blurry": blur_score < blur_threshold
        }
    except Exception as e:
        return {
            "url": url,
            "width": None,
            "height": None,
            "blur_score": None,
            "is_low_res": True,
            "is_blurry": True,
            "error": str(e)
        }

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if 'url' not in df.columns:
        st.error("CSV must contain a 'url' column")
    else:
        urls = df['url'].dropna().unique().tolist()
        st.write(f"Processing {len(urls)} images...")

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_image, urls))

        results_df = pd.DataFrame(results)
        st.dataframe(results_df)

        low_quality = results_df[(results_df['is_low_res']) | (results_df['is_blurry'])]
        st.subheader("Low Quality Images")
        st.dataframe(low_quality)

        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results CSV", data=csv, file_name="image_quality_results.csv")
