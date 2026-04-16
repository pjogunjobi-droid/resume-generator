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
st.markdown("Upload a PDF **or** paste your resume text, then provide a job description.")

# API key input
api_key = st.text_input("DeepSeek API Key", type="password", help="Get your key from platform.deepseek.com")

# ------------------ Positioning Mode Selection ------------------
positioning_mode = st.radio(
    "Resume positioning mode:",
    [
        "Auto-detect",
        "Food/Beverage focused",
        "Industry-neutral (minimize domain language)",
        "Pharma/Medical Devices",
        "Project Management",
        "Other (specify)"
    ]
)

other_text = ""
if positioning_mode == "Other (specify)":
    other_text = st.text_input("Specify target role/industry:", placeholder="e.g., Supply Chain Manager in Tech")

# ------------------ Resume Input (PDF or Text) ------------------
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

# ------------------ Job Description Input ------------------
job_desc = st.text_area("Paste the job description", height=150)

# ------------------ Helper: Build Positioning Instruction ------------------
def get_positioning_instruction(mode, other_text=""):
    if mode == "Auto-detect":
        return """
**Positioning Mode: Auto-detect**
Before rewriting, analyze the job description and identify:
(1) the industry the employer operates in
(2) the function being hired for
(3) the terminology that employer uses for the work being described
Then rewrite the resume using that employer's own language and framing. Do not impose the candidate's industry terminology onto a posting from a different industry.
"""
    elif mode == "Food/Beverage focused":
        return """
**Positioning Mode: Food/Beverage focused**
The target role is in the food or beverage industry. The candidate's domain experience is directly relevant. Preserve all industry-specific terminology and emphasize domain expertise. Prioritize food safety, quality systems, and regulatory compliance experience in food manufacturing.
"""
    elif mode == "Industry-neutral (minimize domain language)":
        return """
**Positioning Mode: Industry-neutral**
Before rewriting, read the candidate's resume and identify every term, phrase, or reference that would signal to a reader that this person works in food or beverage manufacturing. Then ask: does this term have a direct equivalent in the target industry or in general professional language? If yes, use the equivalent. If no direct equivalent exists, describe the underlying function in plain language that would be recognized across any regulated or operational environment.

The goal is not to hide experience — it is to express the same experience in language that resonates with a hiring manager who has never worked in food. A compliance program is a compliance program whether it governs cereal or software. A cross-functional project is a cross-functional project whether the deliverable is a new product or a new policy.

Do not produce a generic resume. The rewrite must still be specific, outcomes-focused, and grounded in what the candidate actually did. Just express it in the language of the role, not the language of the industry.
"""
    elif mode == "Pharma/Medical Devices":
        return """
**Positioning Mode: Pharma/Medical Devices**
The candidate has quality systems and regulatory affairs experience in food manufacturing and formal regulatory training through a Graduate Certificate in Regulatory Affairs. Before rewriting, identify which aspects of their experience map directly to pharma or medical device quality systems (CAPA, audit programs, document control, change control, regulatory submissions, GMP). Prioritize those connections. Where food-specific language exists, ask whether a pharma hiring manager would recognize the equivalent — if yes, use the pharma equivalent. If the candidate's training covers a requirement directly (e.g., ISO 13485, ICH GCP, eCTD submissions), surface that training explicitly.
"""
    elif mode == "Project Management":
        return """
**Positioning Mode: Project Management**
The candidate is targeting a project management role. Before rewriting, analyze the job description and identify:
(1) What type of PM work is being hired for — is this delivery focused (timelines, milestones, cross-functional execution), governance focused (reporting, documentation, stakeholder management), or strategic focused (portfolio, risk, resource planning)?
(2) What does the employer actually need this person to own — are they running projects independently, coordinating between teams, managing vendors, or reporting upward to leadership?
(3) What methodology language does this employer use — waterfall, agile, PMBOK, PRINCE2, or none at all?

Then rewrite the resume to answer those three questions using evidence from the candidate's actual experience. Apply these principles:

**SURFACE THE PM WORK THAT ALREADY EXISTS:** The candidate has led product launches, managed cross-functional teams, built project timelines, handled stakeholder reporting, managed budgets, ran trials, and delivered initiatives from initiation through completion. This is real PM work even if the job title was not 'Project Manager'. Lead every bullet with the project management function — planning, coordinating, delivering, tracking, escalating, reporting — not the technical or quality function it was in service of.

**REFRAME QUALITY AND COMPLIANCE WORK AS PM WORK WHERE TRUE:** A HACCP certification project is a project. A supplier qualification program is a vendor management initiative. A CAPA program is a structured problem resolution process with owners, timelines, and outcomes. A product launch coordinated across R&D, Procurement, and Operations is cross-functional project delivery. Express these as project outcomes, not quality activities.

**LEAD WITH OUTCOMES AND SCOPE:** Every bullet should answer 'what was delivered, to what scale, with what result?' not 'what did the candidate do every day?' Example: not 'coordinated with cross-functional teams' but 'delivered 4 product launches on schedule by coordinating across R&D, Procurement, and Operations, resolving 3 critical path delays before they impacted launch dates.'

**CREDENTIALS:** The candidate holds a PMP certification. Surface this prominently in the summary and skills section. It is the primary credential for this role family and should be the first thing a hiring manager sees.
"""
    elif mode == "Other (specify)" and other_text:
        return f"""
**Positioning Mode: Other – {other_text}**
The candidate is targeting a role in: {other_text}.
Before rewriting, reason through the following:
(1) What does success look like in this role and industry?
(2) Which parts of the candidate's background most directly support that definition of success?
(3) What language does this industry use for the work the candidate has actually done?
Then rewrite the resume to answer question 1 using evidence from question 2 expressed in the language of question 3.
"""
    else:
        return ""

# ------------------ Helper: PDF Generation ------------------
def create_pdf_from_text(content_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.8*inch, bottomMargin=0.8*inch,
                            leftMargin=0.8*inch, rightMargin=0.8*inch)
    styles = getSampleStyleSheet()
    # Custom styles – use unique names
    styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Heading1'],
                              fontSize=14, spaceAfter=12, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='SectionHead', parent=styles['Heading2'],
                              fontSize=12, spaceBefore=10, spaceAfter=6,
                              textTransform='uppercase'))
    # FIX: Renamed from 'Bullet' to 'CustomBullet' to avoid conflict
    styles.add(ParagraphStyle(name='CustomBullet', parent=styles['Normal'],
                              leftIndent=20, bulletIndent=10, spaceAfter=4))
    
    story = []
    lines = content_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith('PROFESSIONAL SUMMARY') or line.startswith('SKILLS') or \
           line.startswith('PROFESSIONAL EXPERIENCE') or line.startswith('EDUCATION'):
            story.append(Paragraph(line, styles['SectionHead']))
        elif line.startswith('-') or line.startswith('•'):
            # Use the new name here too
            story.append(Paragraph(f'• {line[1:].strip()}', styles['CustomBullet']))
        else:
            story.append(Paragraph(line, styles['Normal']))
        story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ------------------ Generation & Scoring ------------------
if st.button("Generate & Score Optimized Resume"):
    if not api_key:
        st.error("Please enter your DeepSeek API key")
    elif not resume_text:
        st.warning("Please provide your resume (upload PDF or paste text)")
    elif not job_desc:
        st.warning("Please paste a job description")
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        
        # Build the full system prompt with ATS rules + positioning mode
        positioning_instruction = get_positioning_instruction(positioning_mode, other_text)
        
        ats_system_prompt = f"""
You are an expert ATS resume optimizer. Your task is to perform a **gap analysis** and rewrite the user's resume to achieve **≥90% alignment** with the job description.

**General Rules (always apply):**
- Achieve ≥90% alignment: every major JD responsibility must be clearly reflected
- Use exact keyword mirroring from the job description
- Prioritize rewriting the MOST RELEVANT experience first
- Preserve and strengthen quantified achievements (%, $, scale, impact). If metrics are missing, infer reasonable estimates.
- Avoid vague phrases like "responsible for"
- Use standard headings: PROFESSIONAL SUMMARY, SKILLS, PROFESSIONAL EXPERIENCE, EDUCATION
- Summary: concise and role-targeted (2–3 sentences max)
- Bullet points: action + outcome (with metrics wherever possible)
- No tables, no graphics, ATS-friendly plain text

{positioning_instruction}

**Critical Reframing Rule:** If a requirement appears missing, assume the user has related experience and infer the strongest truthful framing based on their roles.

**Validation:** Ensure at least 90% of job description requirements are reflected. If not, refine before output.

Only output the final resume – no analysis, no extra text.
"""
        # Step 1: Generate optimized resume
        with st.spinner("Step 1/2: Generating optimized resume..."):
            gen_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": ats_system_prompt},
                    {"role": "user", "content": f"Job Description:\n{job_desc}\n\nUser's Resume:\n{resume_text}\n\nProduce the optimized resume with ≥90% alignment. Add quantified achievements (%, $, time saved, etc.) wherever possible, even if inferred reasonably."}
                ],
                temperature=0.35
            )
            optimized_resume = gen_response.choices[0].message.content
        
        # Step 2: Enhanced scoring
        with st.spinner("Step 2/2: Scoring alignment and analyzing keywords..."):
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
- alignment_score: percentage of key JD requirements clearly reflected in the resume. Be strict (partial = 0.5).
- top_gaps: 2-3 most critical missing or weak areas.
- keyword_coverage: extract 6-10 key technical/keyword phrases from JD, assign status.
- specific_recommendations: actionable, concrete suggestions to improve alignment (e.g., "Add a bullet about CAPA experience using the term 'corrective action'", "Quantify the cross-functional coordination with number of teams or projects").
Only output valid JSON, no extra text.
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
            except Exception as e:
                alignment_score = 0
                top_gaps = ["Could not parse evaluation"]
                keyword_coverage = []
                specific_recommendations = ["Try re-running the generation."]
        
        # Display results
        st.subheader("📊 Alignment Score")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Score", f"{alignment_score}%")
            if alignment_score >= 90:
                st.success("✅ ≥90% target achieved")
            else:
                st.warning(f"⚠️ Below 90% – review gaps and recommendations")
        with col2:
            if top_gaps:
                st.write("**Top gaps / weak areas:**")
                for gap in top_gaps:
                    st.write(f"- {gap}")
            else:
                st.write("No major gaps detected.")
        
        # Display keyword coverage
        if keyword_coverage:
            st.subheader("🔍 Keyword Coverage")
            kw_status_colors = {"covered": "✅", "partial": "⚠️", "gap": "❌"}
            for kw in keyword_coverage:
                status = kw.get("status", "gap")
                st.write(f"{kw_status_colors.get(status, '❌')} **{kw.get('keyword', '')}** – {status}")
        
        # Display specific recommendations
        if specific_recommendations:
            st.subheader("💡 Recommendations to Improve")
            for rec in specific_recommendations:
                st.write(f"- {rec}")
        
        st.markdown("---")
        st.subheader("📄 Optimized Resume")
        st.markdown("---")
        st.write(optimized_resume)
        st.markdown("---")
        
        # PDF download button
        if optimized_resume:
            pdf_buffer = create_pdf_from_text(optimized_resume)
            st.download_button(
                label="📥 Download as PDF",
                data=pdf_buffer,
                file_name="optimized_resume.pdf",
                mime="application/pdf"
            )
        
        st.caption("Tip: You can also copy the text above into Word/Google Docs for final formatting.")
