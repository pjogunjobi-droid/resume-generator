import streamlit as st
import pdfplumber
from openai import OpenAI
import io
import re

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 DeepSeek Resume Optimizer")
st.markdown("Upload your resume (PDF) and paste a job description. The AI will optimize and then score the result.")

# API key input
api_key = st.text_input("DeepSeek API Key", type="password", help="Get your key from platform.deepseek.com")

# PDF upload
uploaded_file = st.file_uploader("Upload your current resume (PDF)", type=["pdf"])
resume_text = ""
if uploaded_file is not None:
    try:
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text()
        if resume_text.strip():
            st.success(f"✅ Resume loaded ({len(resume_text)} chars)")
        else:
            st.error("Could not extract text. Ensure PDF has selectable text.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Job description input
job_desc = st.text_area("Paste the job description", height=150)

if st.button("Generate & Score Optimized Resume"):
    if not api_key:
        st.error("Please enter your DeepSeek API key")
    elif not resume_text:
        st.warning("Please upload a PDF resume")
    elif not job_desc:
        st.warning("Please paste a job description")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

        # ---------- Step 1: Generate Optimized Resume ----------
        with st.spinner("Step 1/2: Generating optimized resume..."):
            gen_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """
You are an expert ATS resume optimizer. Your task is to perform a **gap analysis** and rewrite the user's resume to achieve **≥90% alignment** with the job description.

**Step 1 – Structured Gap Analysis (internal)**
Extract and organize:
- Key Responsibilities
- Technical Skills & Tools
- Leadership / Ownership Expectations
- Regulatory / Domain Knowledge
- Key Keywords / Phrases

Compare against the user's resume and identify missing or weak areas.

**Step 2 – Rewrite for Alignment**
- Achieve ≥90% alignment: every major JD responsibility must be clearly reflected
- Use exact keyword mirroring from the job description
- Prioritize rewriting the MOST RELEVANT experience first
- De-emphasize or remove less relevant content if needed
- Preserve and strengthen quantified achievements (%, $, scale, impact). If metrics are missing, infer reasonable estimates based on role (e.g., "improved efficiency by 20%")
- Avoid vague phrases like "responsible for"

**Critical Reframing Rule**
- If a requirement appears missing, assume the user has related experience and infer the strongest truthful framing based on their roles

**Step 3 – Output Requirements**
Use standard headings:
PROFESSIONAL SUMMARY
SKILLS
PROFESSIONAL EXPERIENCE
EDUCATION

- Summary: concise and role-targeted (2–3 sentences max)
- Bullet points: action + outcome (with metrics wherever plausible)
- ATS-friendly formatting only (no tables, no graphics)

**Step 4 – Validation (MANDATORY)**
- Ensure at least 90% of job description requirements are reflected
- If not, refine the resume before output

Only output the final resume – no analysis, no extra text.
"""},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nUser's Resume:\n{resume_text}\n\nProduce the optimized resume with ≥90% alignment. Add quantified achievements (%, $, time saved, etc.) wherever possible, even if inferred reasonably."}
                ],
                temperature=0.35
            )
            optimized_resume = gen_response.choices[0].message.content

        # ---------- Step 2: Score the Generated Resume ----------
        with st.spinner("Step 2/2: Scoring alignment and identifying top gaps..."):
            score_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """
You are an ATS resume evaluator. Compare the generated resume against the job description.

Output a JSON object with exactly these fields:
{
  "alignment_score": integer (0-100),
  "top_gaps": ["gap1", "gap2", "gap3"]  // max 3 missing/weak areas
}

Rules:
- Score = percentage of key JD requirements clearly reflected in the resume.
- Be strict: if a requirement is only partially addressed, count it as 0.5.
- Gaps should be specific (e.g., "missing SQL", "leadership not quantified").
- Only output valid JSON, no extra text.
"""},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nGenerated Resume:\n{optimized_resume}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            import json
            try:
                eval_data = json.loads(score_response.choices[0].message.content)
                alignment_score = eval_data.get("alignment_score", 0)
                top_gaps = eval_data.get("top_gaps", [])
            except:
                alignment_score = 0
                top_gaps = ["Could not parse evaluation"]

        # ---------- Display Results ----------
        st.subheader("📊 Alignment Score")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Score", f"{alignment_score}%")
            if alignment_score >= 90:
                st.success("✅ ≥90% target achieved")
            else:
                st.warning(f"⚠️ Below 90% – review gaps below")
        with col2:
            if top_gaps:
                st.write("**Top gaps / weak areas:**")
                for gap in top_gaps:
                    st.write(f"- {gap}")
            else:
                st.write("No major gaps detected.")

        st.markdown("---")
        st.subheader("📄 Optimized Resume")
        st.markdown("---")
        st.write(optimized_resume)
        st.markdown("---")
        st.caption("Tip: Copy this text into Word/Google Docs for final formatting.")
