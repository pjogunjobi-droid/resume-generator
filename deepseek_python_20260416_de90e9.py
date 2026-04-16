import streamlit as st
import pdfplumber
from openai import OpenAI
import io
import json
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 DeepSeek Resume Optimizer")
st.markdown("Upload a PDF or paste your resume, then provide a job description.")

# ---------- API Key ----------
api_key = st.text_input("DeepSeek API Key", type="password", help="Get your key from platform.deepseek.com")

# ---------- Resume Positioning Mode ----------
positioning_mode = st.radio(
    "Resume positioning mode:",
    ["Auto-detect", "Food/Beverage focused", "Industry-neutral (minimize domain language)", "Pharma/Medical Devices", "Other (specify)"]
)

other_industry = ""
if positioning_mode == "Other (specify)":
    other_industry = st.text_input("Specify target industry/role")

# ---------- Resume Input (PDF or text) ----------
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
    resume_text = st.text_area("Paste your resume text", height=200, placeholder="Copy and paste your resume here...")

# ---------- Job Description ----------
job_desc = st.text_area("Paste the job description", height=150)

# ---------- Helper: Build positioning instruction ----------
def get_positioning_instruction(mode, other_text=""):
    if mode == "Auto-detect":
        return """
Before rewriting, analyze the job description and identify:
(1) the industry the employer operates in
(2) the function being hired for
(3) the terminology that employer uses for the work being described
Then rewrite the resume using that employer's own language and framing. Do not impose the candidate's industry terminology onto a posting from a different industry.
"""
    elif mode == "Food/Beverage focused":
        return """
The target role is in the food or beverage industry. The candidate's domain experience is directly relevant. Preserve all industry-specific terminology and emphasize domain expertise. Prioritize food safety, quality systems, and regulatory compliance experience in food manufacturing.
"""
    elif mode == "Industry-neutral (minimize domain language)":
        return """
Before rewriting, read the candidate's resume and identify every term, phrase, or reference that would signal to a reader that this person works in food or beverage manufacturing. Then ask: does this term have a direct equivalent in the target industry or in general professional language? If yes, use the equivalent. If no direct equivalent exists, describe the underlying function in plain language that would be recognized across any regulated or operational environment.

The goal is not to hide experience — it is to express the same experience in language that resonates with a hiring manager who has never worked in food. A compliance program is a compliance program whether it governs cereal or software. A cross-functional project is a cross-functional project whether the deliverable is a new product or a new policy.

Do not produce a generic resume. The rewrite must still be specific, outcomes-focused, and grounded in what the candidate actually did. Just express it in the language of the role, not the language of the industry.
"""
    elif mode == "Pharma/Medical Devices":
        return """
The candidate has quality systems and regulatory affairs experience in food manufacturing and formal regulatory training through a Graduate Certificate in Regulatory Affairs. Before rewriting, identify which aspects of their experience map directly to pharma or medical device quality systems (CAPA, audit programs, document control, change control, regulatory submissions, GMP). Prioritize those connections. Where food-specific language exists, ask whether a pharma hiring manager would recognize the equivalent — if yes, use the pharma equivalent. If the candidate's training covers a requirement directly (e.g., ISO 13485, ICH GCP, eCTD submissions), surface that training explicitly.
"""
    elif mode == "Other (specify)":
        return f"""
The candidate is targeting a role in: {other_text}.
Before rewriting, reason through the following:
(1) What does success look like in this role and industry?
(2) Which parts of the candidate's background most directly support that definition of success?
(3) What language does this industry use for the work the candidate has actually done?
Then rewrite the resume to answer question 1 using evidence from question 2 expressed in the language of question 3.
"""
    return ""

# ---------- PDF Generation Function ----------
def create_pdf_resume(content_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.7*inch, bottomMargin=0.7*inch)
    styles = getSampleStyleSheet()
    # Custom styles
    styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Heading1'], fontSize=14, spaceAfter=12))
    styles.add(ParagraphStyle(name='SectionHead', parent=styles['Heading2'], fontSize=12, spaceAfter=6, spaceBefore=12))
    styles.add(ParagraphStyle(name='Bullet', parent=styles['Normal'], leftIndent=20, bulletIndent=10, fontSize=10, leading=12))
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=10, leading=12))
    
    story = []
    lines = content_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        # Detect section headings (all caps or common headers)
        if line.upper() == line and len(line) > 3 and line.isupper():
            story.append(Paragraph(line, styles['SectionHead']))
        elif line.startswith('-') or line.startswith('•'):
            story.append(Paragraph(f'• {line[1:].strip()}', styles['Bullet']))
        else:
            story.append(Paragraph(line, styles['NormalSmall']))
        story.append(Spacer(1, 4))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------- Main Generation ----------
if st.button("Generate & Score Optimized Resume"):
    if not api_key:
        st.error("Please enter your DeepSeek API key")
    elif not resume_text:
        st.warning("Please provide your resume (upload PDF or paste text)")
    elif not job_desc:
        st.warning("Please paste a job description")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        
        # Build system prompt with positioning instruction
        positioning_instruction = get_positioning_instruction(positioning_mode, other_industry)
        system_prompt = f"""
You are an expert ATS resume optimizer. Your task is to perform a **gap analysis** and rewrite the user's resume to align with the job description as strongly as possible.

**Step 1 – Structured Gap Analysis (internal)**
Extract and organize:
- Key Responsibilities
- Technical Skills & Tools
- Leadership / Ownership Expectations
- Regulatory / Domain Knowledge
- Key Keywords / Phrases

Compare against the user's resume and identify missing or weak areas.

**Step 2 – Rewrite for Alignment**
- Use exact keyword mirroring from the job description
- Prioritize rewriting the MOST RELEVANT experience first
- De-emphasize or remove less relevant content if needed
- **Metric rule:** Only include metrics and achievements that are explicitly stated or directly implied by a clear before/after comparison in the user's resume. If a bullet has no metric, reframe it to lead with the action and outcome using strong, specific language without numbers. You are still expected to rewrite bullets aggressively. Reframing, restructuring, and mirroring the JD's exact terminology is required. The only restriction is on fabricating numbers. Everything else — phrasing, emphasis, ordering, keyword mirroring — should be optimized as strongly as possible.
- Avoid vague phrases like "responsible for"

**Critical Reframing Rule**
- If a requirement appears missing, assume the user has related experience and infer the strongest truthful framing based on their roles

**Positioning Mode Instruction**
{positioning_instruction}

**JD KEYWORD PRECEDENCE RULE:**
Positioning mode controls how you frame the candidate's background and which industry language you use for their experience. It does not override the job description's own terminology.

If the job description uses a specific term — regardless of positioning mode — mirror that term exactly in the resume. Do not neutralize, substitute, or omit a keyword that appears in the job description.

Examples:
- JD says 'CAPA' → use 'CAPA', even in neutral mode
- JD says 'change control' → use 'change control', even if the candidate's resume says 'change management'
- JD says 'ISO 13485' → use 'ISO 13485', even if the candidate has never worked in medical devices but has studied it

The positioning mode applies to the candidate's own experience language. The JD's language is always preserved verbatim.

**ALIGNMENT TARGET:**
Achieve the highest possible alignment using only what genuinely exists in the candidate's resume. There is no mandatory score floor.

If after honest rewriting a gap remains because the candidate truly lacks the experience — do not invent content, do not overstate a connection, and do not fabricate a metric to close the gap. Output the strongest honest version of the resume.

**Step 3 – Output Requirements**
Use standard headings:
PROFESSIONAL SUMMARY
SKILLS
PROFESSIONAL EXPERIENCE
EDUCATION

- Summary: concise and role-targeted (2–3 sentences max)
- Bullet points: action + outcome (with metrics only if originally present or directly implied)
- ATS-friendly formatting only (no tables, no graphics)

Only output the final resume – no analysis, no extra text.
"""
        # Step 1: Generate optimized resume
        with st.spinner("Step 1/2: Generating optimized resume..."):
            gen_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nUser's Resume:\n{resume_text}\n\nProduce the optimized resume following all the rules above."}
                ],
                temperature=0.35
            )
            optimized_resume = gen_response.choices[0].message.content

        # Step 2: Enhanced scoring
        with st.spinner("Step 2/2: Scoring alignment and identifying gaps..."):
            score_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """
You are an ATS resume evaluator. Compare the generated resume against the job description.

Output a JSON object with exactly these fields:
{
  "alignment_score": integer (0-100),
  "top_gaps": ["gap1", "gap2", "gap3"],
  "keyword_coverage": [{"keyword": "example", "status": "covered|partial|gap"}],
  "specific_recommendations": ["recommendation1", "recommendation2", "recommendation3"]
}

Rules:
- Score = percentage of key JD requirements clearly reflected in the resume. Be strict: partial = 0.5.
- top_gaps: up to 3 most critical missing or weak areas.
- keyword_coverage: extract 5-8 most important keywords from JD, assign status.
- specific_recommendations: 2-3 actionable, concrete improvements.
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
                recommendations = eval_data.get("specific_recommendations", [])
            except Exception as e:
                alignment_score = 0
                top_gaps = ["Could not parse evaluation"]
                keyword_coverage = []
                recommendations = []

        # ---------- Display Results ----------
        st.subheader("📊 Alignment Score")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Score", f"{alignment_score}%")
            # No threshold check – just informative
            st.caption("Score reflects honest alignment; lower scores indicate experience gaps.")
        with col2:
            if top_gaps:
                st.write("**Top gaps / weak areas:**")
                for gap in top_gaps:
                    st.write(f"- {gap}")
            else:
                st.write("No major gaps detected.")
        
        if keyword_coverage:
            st.write("**Keyword coverage:**")
            for item in keyword_coverage:
                status_emoji = {"covered": "✅", "partial": "⚠️", "gap": "❌"}
                st.write(f"{status_emoji.get(item['status'], '❓')} **{item['keyword']}** – {item['status']}")
        
        if recommendations:
            st.write("**Specific recommendations to improve:**")
            for rec in recommendations:
                st.write(f"- {rec}")

        st.markdown("---")
        st.subheader("📄 Optimized Resume")
        st.markdown("---")
        st.write(optimized_resume)
        st.markdown("---")
        
        # PDF Download Button
        pdf_buffer = create_pdf_resume(optimized_resume)
        st.download_button(
            label="📥 Download as PDF",
            data=pdf_buffer,
            file_name="optimized_resume.pdf",
            mime="application/pdf"
        )
        st.caption("Tip: Review the resume and make any final edits before sending.")