import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 DeepSeek Resume Optimizer")

# Get API key – either from secrets or user input
api_key = st.secrets.get("DEEPSEEK_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your DeepSeek API key", type="password")

resume = st.text_area("Paste your current resume", height=200)
job_desc = st.text_area("Paste the job description", height=150)

if st.button("Generate Optimized Resume"):
    if not api_key:
        st.error("Please provide your DeepSeek API key")
    elif not resume or not job_desc:
        st.warning("Please fill both fields")
    else:
        with st.spinner("DeepSeek is writing..."):
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are an expert resume writer. Rewrite the resume for the job. Use action verbs, quantify achievements, include keywords."},
                    {"role": "user", "content": f"Resume:\n{resume}\n\nJob Description:\n{job_desc}"}
                ],
                temperature=0.4
            )
            st.subheader("Optimized Resume")
            st.write(response.choices[0].message.content)