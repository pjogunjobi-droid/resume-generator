import streamlit as st
import pdfplumber
from openai import OpenAI
import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 DeepSeek Resume Optimizer")
st.markdown("Upload a PDF **or** paste your resume text, choose positioning mode, then provide a job description.")

# API key input
api_key = st.text_input("DeepSeek API Key", type="password", help="Get your key from platform.deepseek.com")

# Resume input method
input_method = st.radio("Resume input method:", ["Upload PDF", "Paste text"])

resume_text = ""

if input_method == "Upload PDF":
    uploaded_file = st.file_uploader("Upload your current resume (PDF)", type=["pdf"])
    if uploaded_file is not None:
        try:
            with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                for page in pdf.pages:
                    resume_text += page.extract_text()
            if resume_text.strip():
                st.success(f"✅ PDF loaded ({len(resume_text)} chars)")
            else:
                st.error("Could not extract text. Ensure PDF has selectable text.")
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
else:
    resume_text = st.text_area("Paste your resume text", height=200, 
                               placeholder="Copy and paste your resume here...")

# Resume positioning mode
positioning_mode = st.selectbox(
    "Resume positioning mode",
    ["Auto-detect", "Food/Beverage focused", "Industry-neutral (minimize domain language)", 
     "Pharma/Medical Devices", "Other (specify)"]
)

other_mode = ""
if positioning_mode == "Other (specify)":
    other_mode = st.text_input("Specify industry/role focus", placeholder="e.g., SaaS sales, Non-profit management")

# Job description input
job_desc = st.text_area("Paste the job description", height=150)

# Function to generate PDF
def create_pdf(content_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.7*inch, bottomMargin=0.7*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, spaceAfter=12, alignment=TA_CENTER)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=12, spaceBefore=10, spaceAfter=6)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=10, leftIndent=20, bulletIndent=10, spaceAfter=4)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    
    story = []
    
    # Process lines
    lines = content_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
        elif line.isupper() and len(line) < 40:  # Assume section headers are all caps
            story.append(Paragraph(line, heading_style))
        elif line.startswith('-') or line.startswith('•'):
            story.append(Paragraph(f'• {line[1:].strip()}', bullet_style))
        else:
            story.append(Paragraph(line, normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

if st.button("Generate & Score Optimized Resume"):
    if not api_key:
        st.error("Please enter your DeepSeek API key")
    elif not resume_text:
        st.warning("Please provide your resume (upload PDF or paste text)")
    elif not job_desc:
        st.warning("Please paste a job description")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        
        # Build positioning instruction
        mode_instruction = ""
        if positioning_mode == "Food/Beverage focused":
            mode_instruction = "Emphasize food/beverage industry experience, quality standards (HACCP, GMP), supply chain, and food safety terminology."
        elif positioning_mode == "Industry-neutral (minimize domain language)":
            mode_instruction = "Remove or minimize food/beverage terminology. Instead, emphasize transferable skills: compliance, project management, continuous improvement, cross-functional collaboration, and operational efficiency."
        elif positioning_mode == "Pharma/Medical Devices":
            mode_instruction = "Highlight regulatory compliance (FDA, ISO 13485), validation processes, documentation, and risk management. Use pharma/medical device terminology."
        elif positioning_mode == "Other (specify)":
            mode_instruction = f"Tailor the resume to the following industry/role: {other_mode}. Use relevant terminology and emphasize transferable skills."
        else:  # Auto-detect
            mode_instruction = "Analyze the job description and user's resume to determine the most appropriate industry focus. Do not force domain language unless clearly supported."

        # Step 1: Generate optimized resume
        with st.spinner("Step 1/2: Generating optimized resume..."):
            gen_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": f"""
You are an expert ATS resume optimizer. Your task is to perform a **gap analysis** and rewrite the user's resume to achieve **≥90% alignment** with the job description.

**Resume Positioning Mode:**
{mode_instruction}

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
- Preserve and strengthen quantified achievements (%, $, scale, impact) that are **explicitly stated or strongly supported** in the user's resume. **DO NOT invent numbers.**
- Avoid vague phrases like "responsible for"
- If a metric is missing, reframe the bullet to emphasize what IS documented (e.g., "Led initiative to reduce waste" instead of "reduced waste by 20%").

**Critical Reframing Rule**
- If a requirement appears missing, assume the user has related experience and infer the strongest truthful framing based on their roles.

**Step 3 – Output Requirements**
Use standard headings:
PROFESSIONAL SUMMARY
SKILLS
PROFESSIONAL EXPERIENCE
EDUCATION

- Summary: concise and role-targeted (2–3 sentences max)
- Bullet points: action + outcome (use only supported metrics)
- ATS-friendly formatting only (no tables, no graphics)

**Step 4 – Validation (MANDATORY)**
- Ensure at least 90% of job description requirements are reflected
- If not, refine the resume before output

Only output the final resume – no analysis, no extra text.
"""},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nUser's Resume:\n{resume_text}\n\nProduce the optimized resume with ≥90% alignment. Use only explicitly supported metrics; do not invent numbers."}
                ],
                temperature=0.35
            )
            optimized_resume = gen_response.choices[0].message.content

        # Step 2: Enhanced scoring
        with st.spinner("Step 2/2: Analyzing alignment, keyword coverage, and recommendations..."):
            score_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """
You are an ATS resume evaluator. Compare the generated resume against the job description.

Output a JSON object with exactly these fields:
{
  "alignment_score": integer (0-100),
  "top_gaps": ["gap1", "gap2", "gap3"],
  "keyword_coverage": [
    {"keyword": "SQL", "status": "covered"},
    {"keyword": "Python", "status": "partial"},
    {"keyword": "Tableau", "status": "gap"}
  ],
  "specific_recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}

Rules:
- Score = percentage of key JD requirements clearly reflected in the resume (0-100 integer).
- Be strict: partial match = 0.5.
- Keyword coverage: list 5-8 most important keywords from JD; status = "covered" (fully addressed), "partial" (mentioned but weak), or "gap" (missing).
- Recommendations: 2-3 actionable, specific bullets to improve alignment (e.g., "Add a bullet quantifying project management impact").
- Only output valid JSON, no extra text.
"""},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nGenerated Resume:\n{optimized_resume}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            try:
                eval_data = json.loads(score_response.choices[0].message.content)
                alignment_score = eval_data.get("alignment_score", 0)
                top_gaps = eval_data.get("top_gaps", [])
                keyword_coverage = eval_data.get("keyword_coverage", [])
                specific_recommendations = eval_data.get("specific_recommendations", [])
            except:
                alignment_score = 0
                top_gaps = ["Could not parse evaluation"]
                keyword_coverage = []
                specific_recommendations = []

        # Display results
        st.subheader("📊 Alignment Score")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Score", f"{alignment_score}%")
            if alignment_score >= 90:
                st.success("✅ ≥90% target achieved")
            else:
                st.warning(f"⚠️ Below 90% – see recommendations")
        with col2:
            if specific_recommendations:
                st.write("**Specific recommendations to improve:**")
                for rec in specific_recommendations:
                    st.write(f"- {rec}")
        
        # Keyword coverage table
        if keyword_coverage:
            st.subheader("🔍 Keyword Coverage")
            for kw in keyword_coverage:
                status = kw.get("status", "gap")
                if status == "covered":
                    st.success(f"✅ {kw['keyword']} – covered")
                elif status == "partial":
                    st.warning(f"⚠️ {kw['keyword']} – partial")
                else:
                    st.error(f"❌ {kw['keyword']} – gap")
        
        # Top gaps
        if top_gaps:
            st.subheader("📋 Top Gaps")
            for gap in top_gaps:
                st.write(f"- {gap}")
        
        # Optimized resume
        st.markdown("---")
        st.subheader("📄 Optimized Resume")
        st.markdown("---")
        st.write(optimized_resume)
        
        # PDF download button
        st.markdown("---")
        try:
            pdf_buffer = create_pdf(optimized_resume)
            st.download_button(
                label="📥 Download as PDF",
                data=pdf_buffer,
                file_name="optimized_resume.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generation error: {str(e)}")
        
        st.caption("Tip: You can also copy the text above into Word/Google Docs.")
