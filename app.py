import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 DeepSeek Resume Optimizer")
st.markdown("Paste your current resume (raw experience) and a job description. The AI will create a highly optimized, ATS‑friendly resume from scratch.")

# Get API key from secrets or user input
api_key = st.secrets.get("DEEPSEEK_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your DeepSeek API key", type="password")

resume = st.text_area("Your current resume (raw experience)", height=200, 
                      placeholder="Example:\n- Sales associate at XYZ Corp, 2022–2024\n  Handled customer inquiries, processed orders\n- Intern at ABC Inc, 2024\n  Assisted with data analysis, created reports")
job_desc = st.text_area("Job description", height=150)

if st.button("Generate Optimized Resume"):
    if not api_key:
        st.error("Please provide your DeepSeek API key")
    elif not resume or not job_desc:
        st.warning("Please fill both fields")
    else:
        with st.spinner("DeepSeek is writing a highly optimized resume (this takes about 15 seconds)..."):
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """
You are an expert resume writer and ATS strategist. Create a highly optimized resume **from scratch** using the candidate's provided experience, but rewrite everything to align with the job description. Follow these rules strictly:

1. **Targeted Summary** (3-4 lines):
   - Concise, role-specific professional summary.
   - Highlight 2-3 most relevant strengths for THIS job.
   - Every sentence directly supports the target role.
   - Use concrete language, not fluff.

2. **Job Description Analysis**:
   - Extract core responsibilities, required technical competencies, and soft skills.
   - Map the candidate's experience directly to each requirement.
   - Ensure every major requirement in the JD is addressed at least once.

3. **Bullet Points – Impact & Alignment**:
   - Avoid generic duties. Each bullet must demonstrate impact (action + outcome).
   - Include metrics where possible: %, time saved, revenue, efficiency, etc.
   - Incorporate critical thinking, risk-based decisions, cross-functional collaboration, or problem-solving in ambiguous situations.
   - Use equivalent terminology from the job description.

4. **Credibility Check**:
   - Before output, ask: "Would a hiring manager believe this candidate can perform the role without concerns about gaps or credibility?"
   - If not, adjust wording for accuracy, strengthen alignment, improve clarity.

5. **Output Format**:
   - Plain text, clear sections: [Summary], [Work Experience], [Skills], [Education].
   - No invented facts – only use information from the candidate's resume.
   - Prioritize the most relevant experience; less relevant roles can be shortened or omitted.
"""},
                    {"role": "user", "content": f"Resume (raw experience):\n{resume}\n\nJob Description:\n{job_desc}\n\nNow produce the optimized resume following all the rules above. Output only the resume with the sections listed."}
                ],
                temperature=0.4
            )
            st.subheader("📄 Optimized Resume")
            st.markdown("---")
            st.write(response.choices[0].message.content)
            st.markdown("---")
            st.caption("Tip: Copy this text into Word or Google Docs and adjust formatting as needed.")
