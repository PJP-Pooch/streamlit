import streamlit as st
import searchconsole
import pandas as pd
import openai

st.set_page_config(page_title="GSC Meta Tag Generator", page_icon="🔍", layout="centered")

st.title("🔍 GSC-Based Meta Tag Generator")
st.markdown("""
This app connects to your Google Search Console account, pulls top queries by URL,
and uses OpenAI to generate SEO-optimized meta titles and descriptions.
""")

# Step 0: Get OpenAI API Key
openai_api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
if not openai_api_key:
    st.warning("Please enter your OpenAI API Key to continue.")
    st.stop()
openai.api_key = openai_api_key

# Step 1: Authenticate GSC
st.header("Step 1: Connect to Google Search Console")
authenticate_button = st.button("🔐 Sign in with Google")

if authenticate_button:
    try:
        account = searchconsole.authenticate()
        st.session_state["account"] = account
        st.success("✅ Successfully connected to Google Search Console")
    except Exception as e:
        st.error("❌ Authentication failed. Please try again.")
        st.stop()

if "account" not in st.session_state:
    st.info("Please sign in with Google above to access your GSC data.")
    st.stop()

account = st.session_state["account"]

# Step 2: Choose a Property
properties = list(account.keys())
selected_property = st.selectbox("🌐 Choose a web property", properties)
webproperty = account[selected_property]

# Step 3: Set Date Range
st.header("Step 2: Select Date Range")
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

# Step 4: Query GSC
if st.button("📊 Pull GSC Data"):
    with st.spinner("Fetching data from GSC..."):
        report = (
            webproperty.query.range(str(start_date), str(end_date))
            .dimension('page', 'query')
            .get()
        )
        df = report.to_dataframe()
        st.write("Sample data:", df.head())

        # Step 5: Group Queries by Page
        st.header("Step 3: Generate Meta Tags")
        top_queries = (
            df.groupby('page')
            .apply(lambda g: g.sort_values(by=['clicks', 'impressions'], ascending=False).head(3)['query'].tolist())
            .reset_index()
            .rename(columns={0: 'top_queries'})
        )

        # Step 6: Generate with OpenAI
        def generate_meta(url, queries):
            prompt = f"""
            Generate an SEO meta title (max 60 characters) and meta description (max 155 characters) for the page: {url}.
            Base the content on the following top Google Search queries: {', '.join(queries)}.

            Return in this format:
            Title: ...
            Description: ...
            """
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()

        top_queries['meta'] = top_queries.apply(
            lambda row: generate_meta(row['page'], row['top_queries']), axis=1
        )

        # Step 7: Show and Export
        st.dataframe(top_queries)
        csv = top_queries.to_csv(index=False)
        st.download_button("📥 Download Meta Data as CSV", csv, "meta_data.csv", "text/csv")
