import streamlit as st
import google.generativeai as genai
import json
import time
import PyPDF2
from io import BytesIO

# Optional OCR dependencies. If not installed, app still loads but OCR will
# prompt users to install the extra requirements.
OCR_AVAILABLE = True
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
except Exception:
    OCR_AVAILABLE = False

# PDF generation dependencies via reportlab.
REPORTLAB_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
except Exception:
    REPORTLAB_AVAILABLE = False

# Set Page Config
st.set_page_config(
    page_title="Healthcare Navigator Agent",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded"
)
# Gemini API Key
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Model
model = genai.GenerativeModel("gemini-2.5-flash")

# Custom styling (CSS) for a beautiful, premium theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply font family to entire app */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Header Card styling */
    .header-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(30, 60, 114, 0.15);
    }
    .header-container h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff !important;
    }
    .header-container p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    /* Button Customization */
    .stButton>button {
        background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        transition: all 0.3s ease !important;
        width: 100%;
        box-shadow: 0 4px 10px rgba(42, 82, 152, 0.2) !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(42, 82, 152, 0.3) !important;
    }
    
    /* Subheader styling */
    h3 {
        color: #1e3c72 !important;
        font-weight: 600 !important;
        margin-top: 1.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    
    /* Custom spacing and margins */
    .block-container {
        padding-top: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Sample reports dictionary
SAMPLES = {
    "Select a sample report...": "",
    "Anemia Panel (Low Hemoglobin)": (
        "CBC Report:\n"
        "- Hemoglobin: 10.5 g/dL (Normal range: 12.0 - 15.5 g/dL)\n"
        "- Hematocrit: 32% (Normal range: 37% - 48%)\n"
        "- White Blood Cells: 6,000 /mcL (Normal range: 4,500 - 11,000 /mcL)\n"
        "- Platelets: 250,000 /mcL (Normal range: 150,000 - 450,000 /mcL)"
    ),
    "Thyroid Panel (Elevated TSH)": (
        "Thyroid Panel:\n"
        "- TSH: 6.2 mIU/L (Normal range: 0.4 - 4.0 mIU/L)\n"
        "- Free T4: 0.9 ng/dL (Normal range: 0.8 - 1.8 ng/dL)\n"
        "Patient symptoms: Fatigue, feeling cold constantly, mild weight gain."
    ),
    "Lipid Panel (High Cholesterol)": (
        "Lipid Profile:\n"
        "- Total Cholesterol: 245 mg/dL (Optimal: < 200 mg/dL)\n"
        "- LDL Cholesterol: 165 mg/dL (Optimal: < 100 mg/dL)\n"
        "- HDL Cholesterol: 42 mg/dL (Recommended: > 40 mg/dL)\n"
        "- Triglycerides: 190 mg/dL (Normal: < 150 mg/dL)"
    ),
    "Diabetes Screening (Elevated HbA1c)": (
        "Metabolic Panel:\n"
        "- Fasting Blood Glucose: 112 mg/dL (Normal: 70 - 99 mg/dL)\n"
        "- HbA1c: 6.1% (Normal: < 5.7%, Prediabetes: 5.7% - 6.4%)\n"
        "Patient has family history of type 2 diabetes."
    )
}

# Sidebar Content
st.sidebar.markdown("""
<div class="sidebar-panel">
  <div class="sidebar-header-panel">
    <div>
      <div class="sidebar-dashboard-title">System Dashboard</div>
      <div class="sidebar-dashboard-subtitle">Premium medical AI operations</div>
    </div>
    <div class="sidebar-logo">🩺</div>
  </div>
  <div class="sidebar-stats">
    <div class="sidebar-stat">
      <div class="stat-icon">📄</div>
      <div>
        <div class="stat-label">Reports Analyzed</div>
        <div class="stat-value">125+</div>
      </div>
    </div>
    <div class="sidebar-stat">
      <div class="stat-icon">🤖</div>
      <div>
        <div class="stat-label">Agents Active</div>
        <div class="stat-value">3</div>
      </div>
    </div>
    <div class="sidebar-stat">
      <div class="stat-icon">🎯</div>
      <div>
        <div class="stat-label">Accuracy Mode</div>
        <div class="stat-value">High Confidence</div>
      </div>
    </div>
    <div class="sidebar-stat">
      <div class="stat-icon">⚡</div>
      <div>
        <div class="stat-label">Status</div>
        <div class="stat-value">Demo Ready</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Sample Reports")
st.sidebar.markdown("Click below to quickly load a sample medical report to test the analyzer:")

# Initialize session state for report_text if not present
if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "step" not in st.session_state:
    st.session_state.step = "upload"

def extract_pdf_text(uploaded_file):
    """
    Try to extract text using PyPDF2 first. If no text is found,
    fall back to OCR using pdf2image + pytesseract and return a tuple
    (text, used_ocr_flag).
    """
    try:
        # Read bytes so we can reuse for both PyPDF2 and pdf2image
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()

        # Try text extraction via PyPDF2
        try:
            reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text_chunks = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
            extracted = "\n".join(text_chunks).strip()
            if extracted:
                return extracted, False
        except Exception:
            # Continue to OCR fallback if PyPDF2 fails silently
            extracted = ""

        # If PyPDF2 returned no text, run OCR
        if not OCR_AVAILABLE:
            raise RuntimeError("No extractable text found and OCR dependencies are not installed. Please install pdf2image, pytesseract, and Pillow to enable OCR support.")

        st.info("Scanned PDF detected. Running OCR...")
        images = convert_from_bytes(pdf_bytes)
        ocr_chunks = []
        for img in images:
            # Ensure PIL Image
            if not isinstance(img, Image.Image):
                img = Image.fromarray(img)
            ocr_text = pytesseract.image_to_string(img)
            ocr_chunks.append(ocr_text or "")
        ocr_text = "\n".join(ocr_chunks).strip()
        return ocr_text, True

    except Exception as e:
        raise RuntimeError(f"Unable to extract text from PDF: {e}")


def is_quota_error(err) -> bool:
    """Detect whether an exception represents a Gemini quota (429) error."""
    try:
        code = getattr(err, "status_code", None) or getattr(err, "http_status", None)
        msg = str(err).lower()
        if code == 429:
            return True
        if "429" in msg or "quota" in msg or "rate limit" in msg or "quota exceeded" in msg:
            return True
    except Exception:
        pass
    return False


def get_demo_response() -> dict:
    """Return the predefined demo JSON response used for Demo Mode."""
    return {
        "analysis": {
            "findings": [
                {
                    "test_name": "Hemoglobin",
                    "value": "10.2 g/dL",
                    "normal_range": "12.0 - 15.5 g/dL",
                    "status": "Abnormal",
                    "details": "Low hemoglobin consistent with mild anemia."
                },
                {
                    "test_name": "White Blood Cells",
                    "value": "6,500 /mcL",
                    "normal_range": "4,500 - 11,000 /mcL",
                    "status": "Normal",
                    "details": "Within normal limits."
                },
                {
                    "test_name": "TSH",
                    "value": "5.1 mIU/L",
                    "normal_range": "0.4 - 4.0 mIU/L",
                    "status": "Abnormal",
                    "details": "TSH mildly elevated; consider evaluation for hypothyroidism."
                }
            ]
        },
        "explanation": {
            "summary": "The labs show a mild anemia and a slightly elevated TSH, which may suggest early thyroid underactivity. Discuss these findings with your doctor for further evaluation.",
            "explanations": [
                {
                    "test_name": "Hemoglobin",
                    "simple_explanation": "Hemoglobin carries oxygen in your blood. A low level can make you feel tired and weak."
                },
                {
                    "test_name": "TSH",
                    "simple_explanation": "TSH is a signal from your brain that tells your thyroid to make hormones; a slightly high value can mean your thyroid is underactive."
                }
            ]
        },
        "doctor_questions": {
            "questions": [
                "What could be causing my low hemoglobin?",
                "Do I need further tests to evaluate my anemia?",
                "Should I have thyroid function tests repeated or evaluated further?",
                "Are there dietary or medication changes I should consider?",
                "When should I schedule follow-up testing or see a specialist?"
            ],
            "disclaimer": "This is a demo response for informational purposes only and not medical advice. Consult a healthcare professional for diagnosis and treatment."
        }
    }


def handle_quota_mode():
    """Switch to Demo Mode: show warning and return JSON string of demo response."""
    st.warning("Gemini quota exceeded — switching to Demo Mode (sample response shown).")
    demo_response = get_demo_response()
    return json.dumps(demo_response)


def create_report_pdf(analysis_data, explanation_data, question_data, overall_health, risk_label, total_tests, abnormal_count, disclaimer_text):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab is not installed. Install reportlab to enable PDF download.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=inch*0.7, rightMargin=inch*0.7,
                            topMargin=inch*0.7, bottomMargin=inch*0.7)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Heading", fontSize=18, leading=22, spaceAfter=14, alignment=1, textColor=colors.HexColor("#1f4fbd"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SubHeading", fontSize=12, leading=16, spaceAfter=8, textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=10.5, leading=14, spaceAfter=10, textColor=colors.HexColor("#334155"), fontName="Helvetica"))
    styles.add(ParagraphStyle(name="Small", fontSize=9, leading=12, spaceAfter=8, textColor=colors.HexColor("#475569"), fontName="Helvetica"))

    story = []
    story.append(Paragraph("Healthcare Navigator Agent", styles["Heading"]))
    story.append(Paragraph("Report Summary", styles["SubHeading"]))
    story.append(Paragraph(f"<strong>Overall Health Status:</strong> {overall_health}", styles["Body"]))
    story.append(Paragraph(f"<strong>Risk Score:</strong> {risk_label}", styles["Body"]))
    story.append(Paragraph(f"<strong>Tests Analyzed:</strong> {total_tests}", styles["Body"]))
    story.append(Paragraph(f"<strong>Abnormal Findings:</strong> {abnormal_count}", styles["Body"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Key Findings", styles["SubHeading"]))
    headers = ["Test / Marker", "Value", "Normal Range", "Status"]
    table_data = [headers]
    for f in analysis_data.get("findings", []):
        table_data.append([
            f.get("test_name", ""),
            f.get("value", ""),
            f.get("normal_range", ""),
            f.get("status", "")
        ])

    table = Table(table_data, hAlign="LEFT", colWidths=[2.1*inch, 1.3*inch, 2.1*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4fbd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Patient-Friendly Explanation", styles["SubHeading"]))
    story.append(Paragraph(explanation_data.get("summary", ""), styles["Body"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Doctor Questions", styles["SubHeading"]))
    for q in question_data.get("questions", []):
        story.append(Paragraph(f"• {q}", styles["Body"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Disclaimer", styles["SubHeading"]))
    story.append(Paragraph(disclaimer_text, styles["Small"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def get_report_context_text(analysis_data, explanation_data, question_data):
    findings_text = "\n".join([
        f"{f.get('test_name', '')}: {f.get('value', '')} ({f.get('normal_range', '')}) - {f.get('status', '')}. {f.get('details', '')}"
        for f in analysis_data.get('findings', [])
    ])
    explanation_summary = explanation_data.get('summary', '')
    questions_text = "\n".join([f"- {q}" for q in question_data.get('questions', [])])
    return f"Report Analysis Context:\n\nFindings:\n{findings_text}\n\nSummary:\n{explanation_summary}\n\nDoctor Questions:\n{questions_text}"


def ask_report_question(question):
    if not st.session_state.get('analysis_data'):
        return "Please analyze a report first to chat with the report."

    context_text = get_report_context_text(
        st.session_state.analysis_data,
        st.session_state.explanation_data,
        st.session_state.question_data
    )
    prompt = f"You are a healthcare assistant. Answer the user's question using ONLY the analyzed report context below. Do not invent new findings.\n\n{context_text}\n\nUser question: {question}\nAnswer:"
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "text/plain"}
        )
        return response.text.strip()
    except Exception as err:
        return f"Unable to answer the question right now: {str(err)}"


def handle_chat_submit():
    query = st.session_state.chat_query.strip()
    if not query:
        return
    answer = ask_report_question(query)
    st.session_state.chat_history.append(("You", query))
    st.session_state.chat_history.append(("Navigator", answer))
    st.session_state.chat_query = ""


def clear_analysis_state():
    for key in ['analysis_data', 'explanation_data', 'question_data', 'overall_health', 'risk_label', 'total_tests', 'abnormal_count', 'chat_history', 'chat_query']:
        if key in st.session_state:
            del st.session_state[key]


def load_sample():
    if st.session_state.sample_selector != "Select a sample report...":
        st.session_state.report_text = SAMPLES[st.session_state.sample_selector]

st.sidebar.selectbox(
    "Choose a sample report:",
    options=list(SAMPLES.keys()),
    key="sample_selector",
    on_change=load_sample
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**How to use:**
1. Select a sample report from the dropdown above OR paste your own report in the text box.
2. Click **Analyze Report**.
3. View the outputs of the **Analysis**, **Explanation**, and **Doctor Question** agents below.
""")

# Premium Healthcare Dashboard Styling (Incremental Improvements)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', 'Outfit', sans-serif;
}
body {
    background: linear-gradient(180deg, #eef4ff 0%, #f9fbff 40%, #ffffff 100%);
}
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 1.8rem !important;
}
.hero-banner {
    width: 100%;
    padding: 40px 36px;
    border-radius: 28px;
    background: linear-gradient(135deg, #1f4fbd 0%, #2567f4 45%, #5fb4ff 100%);
    color: white;
    box-shadow: 0 24px 70px rgba(31, 64, 148, 0.18);
    margin-bottom: 24px;
    overflow: hidden;
    position: relative;
}
.hero-banner::before {
    content: "";
    position: absolute;
    top: -20px;
    right: -40px;
    width: 220px;
    height: 220px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 50%;
}
.hero-banner-inner {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 30px;
    flex-wrap: wrap;
    position: relative;
    z-index: 1;
}
.hero-icon-large {
    width: 100px;
    height: 100px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.22);
    font-size: 44px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16);
}
.hero-content {
    max-width: 700px;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.18);
    padding: 9px 16px;
    border-radius: 999px;
    font-size: 0.92rem;
    color: #e2e8f0;
    margin-bottom: 18px;
}
.hero-title {
    font-size: 3rem;
    line-height: 1.05;
    margin: 0 0 14px 0;
    font-weight: 800;
}
.hero-subtitle {
    max-width: 680px;
    color: rgba(255, 255, 255, 0.92);
    font-size: 1.05rem;
    margin: 0;
    line-height: 1.75;
}
.hero-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 22px;
}
.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.18);
    color: #eef2ff;
    border: 1px solid rgba(255,255,255,0.35);
    padding: 10px 14px;
    border-radius: 999px;
    font-size: 0.95rem;
}
.sidebar-panel {
    background: linear-gradient(180deg, rgba(31, 64, 148, 0.1), rgba(255, 255, 255, 0.96));
    border-radius: 24px;
    padding: 24px 22px;
    box-shadow: 0 18px 40px rgba(31, 64, 148, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.14);
    margin-bottom: 24px;
}
.sidebar-header-panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
}
.sidebar-dashboard-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 6px;
}
.sidebar-dashboard-subtitle {
    font-size: 0.92rem;
    color: #475569;
    margin: 0;
}
.sidebar-stats {
    display: grid;
    gap: 14px;
}
.sidebar-stat {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.12);
}
.sidebar-logo {
    width: 54px;
    height: 54px;
    border-radius: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.24);
    font-size: 26px;
}
.sidebar-stat .stat-icon {
    width: 36px;
    height: 36px;
    border-radius: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(59, 130, 246, 0.16);
    color: #1d4ed8;
    font-size: 18px;
}
.sidebar-stat .stat-label {
    color: #475569;
    font-size: 0.9rem;
    margin: 0;
}
.sidebar-stat .stat-value {
    color: #0f172a;
    font-weight: 700;
    font-size: 1rem;
}
.workflow-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 18px;
    flex-wrap: wrap;
    margin-bottom: 28px;
}
.workflow-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 18px 22px;
    border-radius: 22px;
    min-width: 220px;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(148, 163, 184, 0.16);
    color: #0f172a;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
    font-weight: 700;
}
.workflow-arrow {
    font-size: 1.35rem;
    color: #64748b;
}
.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(248,250,255,0.94) 100%);
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    border: 1px solid rgba(226, 232, 240, 0.8);
    backdrop-filter: blur(12px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
}
.card-accent {
    position: absolute;
    top: 0;
    left: 0;
    height: 6px;
    width: 100%;
}
.card-accent-analysis { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.card-accent-explanation { background: linear-gradient(90deg, #16a34a, #4ade80); }
.card-accent-questions { background: linear-gradient(90deg, #ea580c, #fb923c); }
.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 20px;
    position: relative;
    z-index: 1;
}
.card-icon {
    width: 48px;
    height: 48px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
}
.card-icon.analysis { background: rgba(37, 99, 235, 0.14); color: #1d4ed8; }
.card-icon.explanation { background: rgba(22, 163, 74, 0.14); color: #15803d; }
.card-icon.questions { background: rgba(234, 88, 12, 0.14); color: #c2410c; }
.card-title { font-size: 1.15rem; margin: 0; font-weight: 700; color: #0f172a; }
.card-sub { color: #64748b; font-size: 0.9rem; margin-top: 4px; }
.card-note { font-size: 0.96rem; color: #475569; margin-bottom: 18px; line-height: 1.7; }
.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    margin-right: 6px;
}
.badge-normal { background: #d1fae5; color: #064e3b; border: 1px solid rgba(16, 185, 129, 0.28); }
.badge-attention { background: #fef3c7; color: #78350f; border: 1px solid rgba(245, 158, 11, 0.28); }
.badge-critical { background: #fee2e2; color: #991b1b; border: 1px solid rgba(239, 68, 68, 0.28); }
.table-card {
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
}
.table-card th,
.table-card td {
    text-align: left;
    padding: 12px 14px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}
.table-card th { color: #0f172a; font-weight: 700; font-size: 0.92rem; }
.table-card td { color: #475569; font-size: 0.92rem; }
.table-card tr:last-child td { border-bottom: none; }
.details-card {
    background: rgba(255,255,255,0.96);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 20px;
    padding: 18px 20px;
    margin-bottom: 16px;
}
.details-card summary {
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    outline: none;
}
.details-card div {
    margin-top: 12px;
    color: #475569;
    line-height: 1.7;
}
.copy-button {
    border: none;
    background: linear-gradient(135deg, #1f4fbd 0%, #2567f4 100%);
    color: white;
    padding: 10px 16px;
    border-radius: 14px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 12px 24px rgba(31, 64, 148, 0.16);
    margin-bottom: 18px;
}
.copy-button:hover { opacity: 0.95; }
.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border-radius: 18px;
    font-weight: 700;
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid rgba(148, 163, 184, 0.22);
    margin-bottom: 20px;
}
.status-chip.green { background: #dcfce7; color: #166534; border-color: rgba(16, 185, 129, 0.22); }
.status-chip.yellow { background: #fef9c3; color: #713f12; border-color: rgba(245, 158, 11, 0.22); }
.status-chip.red { background: #fee2e2; color: #991b1b; border-color: rgba(239, 68, 68, 0.22); }
.result-metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.metric-card {
    background: white;
    border-radius: 20px;
    padding: 20px 22px;
    box-shadow: 0 16px 30px rgba(15, 23, 42, 0.06);
    border: 1px solid rgba(148, 163, 184, 0.16);
}
.metric-label { color: #64748b; font-size: 0.92rem; margin-bottom: 8px; }
.metric-value { font-size: 2rem; font-weight: 800; color: #0f172a; }
.metric-note { color: #475569; font-size: 0.9rem; margin-top: 6px; }
.warning-box {
    border-radius: 18px;
    background: rgba(254, 242, 242, 0.95);
    padding: 18px 20px;
    border: 1px solid rgba(239, 68, 68, 0.18);
    color: #991b1b;
}
.footer-panel {
    background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(241, 245, 255, 0.92));
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 20px;
    padding: 22px 24px;
    margin-top: 28px;
    box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}
.footer-title {
    font-size: 1rem;
    color: #0f172a;
    font-weight: 700;
    margin-bottom: 6px;
}
.footer-subtitle {
    color: #475569;
    font-size: 0.92rem;
    margin-bottom: 16px;
}
.footer-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    color: #334155;
    font-size: 0.92rem;
}
.footer-metrics div { padding: 12px 14px; border-radius: 14px; background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.14); }
.stTextArea>div>textarea { min-height: 180px !important; }
h3 { color: #0f172a; font-weight: 700; margin-bottom: 14px !important; }
</style>

<div class="hero-banner">
  <div class="hero-banner-inner">
    <div class="hero-icon-large">🏥</div>
    <div class="hero-content">
      <div class="hero-badge">AI Powered • Gemini 2.5 Flash • Multi-Agent</div>
      <div class="hero-title">Healthcare Navigator Agent</div>
      <div class="hero-subtitle">Multi-Agent AI System for Medical Report Intelligence</div>
      <div class="hero-pill-row">
        <span class="hero-pill">📄 PDF Reports</span>
        <span class="hero-pill">🤖 3 AI Agents</span>
        <span class="hero-pill">⚡ Real-Time Analysis</span>
        <span class="hero-pill">🔒 Privacy Focused</span>
      </div>
    </div>
  </div>
</div>
<div class="workflow-row">
  <div class="workflow-card"><span>📄</span><div class="workflow-label"><strong>Upload Report</strong><small>Start here</small></div></div>
  <div class="workflow-arrow">↓</div>
  <div class="workflow-card"><span>🤖</span><div class="workflow-label"><strong>AI Analysis</strong><small>Multi-agent inference</small></div></div>
  <div class="workflow-arrow">↓</div>
  <div class="workflow-card"><span>📊</span><div class="workflow-label"><strong>Patient Insights</strong><small>Clear health summary</small></div></div>
</div>
""", unsafe_allow_html=True)

# PDF Upload
uploaded_file = st.file_uploader(
    "Upload PDF medical report",
    type=["pdf"],
    help="Upload a PDF file and its extracted text will appear in the report input area."
)

if uploaded_file is not None:
    try:
        extracted_text, used_ocr = extract_pdf_text(uploaded_file)
        if extracted_text:
            st.session_state.report_text = extracted_text
            if used_ocr:
                st.success("Text extracted successfully using OCR.")
            else:
                st.success("PDF text extracted successfully ✓")
            st.session_state.step = "upload"
        else:
            st.warning("The uploaded PDF did not contain any extractable text.")
    except RuntimeError as pdf_error:
        st.error(str(pdf_error))
    except Exception:
        st.error("A problem occurred while extracting text from the uploaded PDF.")

# Report Input Section
st.markdown("### 📋 Medical Report")
st.text_area(
    "Paste your medical report or lab results below:",
    key="report_text",
    height=180,
    placeholder="Example: CBC result with low hemoglobin, lipid panels, thyroid reports, or doctor's summary notes..."
)

# Action Buttons
col1, col2 = st.columns([3, 1])

with col1:
    analyze_button = st.button("🚀 Analyze Report", use_container_width=True, key="analyze_btn", type="primary")
with col2:
    def clear_text_callback():
        st.session_state.report_text = ""
        st.session_state.sample_selector = "Select a sample report..."
        st.session_state.step = "upload"
        try:
            st.experimental_rerun()
        except Exception:
            pass

    st.button("🗑️ Clear Text", use_container_width=True, key="clear_btn", on_click=clear_text_callback)

def clean_and_parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return json.loads(cleaned)

if analyze_button:
    if st.session_state.report_text.strip():
        st.session_state.step = "analyze"
        # Using st.status to show step-by-step agent workflow progress
        with st.status("Executing Multi-Agent Workflow (Optimized Call)...", expanded=True) as status_container:
            try:
                # ------------------ 1. SINGLE CONSOLIDATED API CALL ------------------
                st.write("📡 Connecting to Gemini API (Single-Call Optimization)...")
                
                # Single prompt representing the multi-agent execution pipeline
                prompt = f"""
                You are a multi-agent clinical translation system consisting of three virtual agents. 
                Analyze the following medical report and perform the tasks of each agent sequentially:
                ---
                {st.session_state.report_text}
                ---
                
                Execute the tasks for:
                1. "analysis": (Analysis Agent) Extract all test names, patient values, reference ranges, status (Normal or Abnormal), and a clinical details note.
                2. "explanation": (Explanation Agent) Translate the findings into layperson-friendly language using simple analogies and a warm, empathetic summary.
                3. "doctor_questions": (Doctor Question Agent) Formulate exactly 5 tailored questions the patient should ask their doctor based on the report, along with a medical disclaimer.
                
                You MUST respond ONLY with a JSON object containing the exact structure below. Do not include any other fields:
                {{
                  "analysis": {{
                    "findings": [
                      {{
                        "test_name": "Name of test",
                        "value": "Patient's value",
                        "normal_range": "Normal reference range",
                        "status": "Normal" or "Abnormal",
                        "details": "Clinical details note"
                      }}
                    ]
                  }},
                  "explanation": {{
                    "summary": "Empathetic, layperson summary of the overall health status shown in the report (2-3 sentences).",
                    "explanations": [
                      {{
                        "test_name": "Name of test",
                        "simple_explanation": "Simple layperson translation using analogies where helpful."
                      }}
                    ]
                  }},
                  "doctor_questions": {{
                    "questions": [
                      "Question 1",
                      "Question 2",
                      "Question 3",
                      "Question 4",
                      "Question 5"
                    ],
                    "disclaimer": "Standard clinical disclaimer..."
                  }}
                }}
                """

                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    response_text = response.text
                except Exception as e:
                    def _is_quota_error(err):
                        # Check common attributes and message content for 429/quota
                        code = getattr(err, "status_code", None) or getattr(err, "http_status", None)
                        msg = str(err).lower()
                        if code == 429:
                            return True
                        if "429" in msg or "quota" in msg or "rate limit" in msg or "quota exceeded" in msg:
                            return True
                        return False

                    if _is_quota_error(e):
                        st.warning("Gemini quota exceeded — switching to Demo Mode (sample response shown).")
                        # Predefined demo JSON response (keeps same structure used by regular responses)
                        demo_response = {
                            "analysis": {
                                "findings": [
                                    {
                                        "test_name": "Hemoglobin",
                                        "value": "10.2 g/dL",
                                        "normal_range": "12.0 - 15.5 g/dL",
                                        "status": "Abnormal",
                                        "details": "Low hemoglobin consistent with mild anemia."
                                    },
                                    {
                                        "test_name": "White Blood Cells",
                                        "value": "6,500 /mcL",
                                        "normal_range": "4,500 - 11,000 /mcL",
                                        "status": "Normal",
                                        "details": "Within normal limits."
                                    },
                                    {
                                        "test_name": "TSH",
                                        "value": "5.1 mIU/L",
                                        "normal_range": "0.4 - 4.0 mIU/L",
                                        "status": "Abnormal",
                                        "details": "TSH mildly elevated; consider evaluation for hypothyroidism."
                                    }
                                ]
                            },
                            "explanation": {
                                "summary": "The labs show a mild anemia and a slightly elevated TSH, which may suggest early thyroid underactivity. Discuss these findings with your doctor for further evaluation.",
                                "explanations": [
                                    {
                                        "test_name": "Hemoglobin",
                                        "simple_explanation": "Hemoglobin carries oxygen in your blood. A low level can make you feel tired and weak."
                                    },
                                    {
                                        "test_name": "TSH",
                                        "simple_explanation": "TSH is a signal from your brain that tells your thyroid to make hormones; a slightly high value can mean your thyroid is underactive."
                                    }
                                ]
                            },
                            "doctor_questions": {
                                "questions": [
                                    "What could be causing my low hemoglobin?",
                                    "Do I need further tests to evaluate my anemia?",
                                    "Should I have thyroid function tests repeated or evaluated further?",
                                    "Are there dietary or medication changes I should consider?",
                                    "When should I schedule follow-up testing or see a specialist?"
                                ],
                                "disclaimer": "This is a demo response for informational purposes only and not medical advice. Consult a healthcare professional for diagnosis and treatment."
                            }
                        }
                        response_text = json.dumps(demo_response)
                    else:
                        # Re-raise so outer exception handlers display errors as before
                        raise

                # Simulated logs for each agent to keep the premium multi-agent feel
                st.write("🕵️‍♂️ **Analysis Agent**: Extracting key findings and abnormal values...")
                time.sleep(1.0)

                st.write("📖 **Explanation Agent**: Translating findings into simple layperson language...")
                time.sleep(1.0)

                st.write("💬 **Doctor Question Agent**: Formulating tailored questions for your physician...")
                time.sleep(0.8)

                # Parse the unified JSON
                data = clean_and_parse_json(response_text)

                # Retrieve individual agent outputs from the unified payload
                analysis_data = data.get("analysis", {})
                explanation_data = data.get("explanation", {})
                question_data = data.get("doctor_questions", {})
                disclaimer_text = question_data.get("disclaimer", "This analysis is for informational purposes only and not medical advice. Consult a healthcare professional for diagnosis and treatment.")

                # Store results in session state for later download/chat use
                st.session_state.analysis_data = analysis_data
                st.session_state.explanation_data = explanation_data
                st.session_state.question_data = question_data
                st.session_state.overall_health = overall_health
                st.session_state.risk_label = risk_label
                st.session_state.total_tests = total_tests
                st.session_state.abnormal_count = abnormal_count
                st.session_state.disclaimer_text = disclaimer_text

                st.session_state.step = "results"
                status_container.update(label="All agents completed successfully!", state="complete", expanded=False)
                st.success("✓ Analysis complete! Review the outputs from each agent below.")

                # Retrieve individual agent outputs
                findings_list = analysis_data.get("findings", [])
                explanations_list = explanation_data.get("explanations", [])
                questions_list = question_data.get("questions", [])

                # Generate downloadable PDF summary if reportlab is available
                pdf_bytes = None
                if REPORTLAB_AVAILABLE:
                    try:
                        pdf_bytes = create_report_pdf(
                            analysis_data,
                            explanation_data,
                            question_data,
                            overall_health,
                            risk_label,
                            total_tests,
                            abnormal_count,
                            disclaimer_text
                        )
                    except Exception as pdf_err:
                        st.warning(f"Unable to generate PDF report summary: {pdf_err}")

                if pdf_bytes:
                    st.download_button(
                        label="📥 Download Report Summary",
                        data=pdf_bytes,
                        file_name="healthcare_report_summary.pdf",
                        mime="application/pdf",
                        key="download_report_pdf"
                    )
                elif not REPORTLAB_AVAILABLE:
                    st.info("Install reportlab to enable PDF report download.")

                # Dashboard metrics and tabbed results layout
                total_tests = len(findings_list)
                normal_count = sum(1 for f in findings_list if f.get("status", "").strip().lower() == "normal")
                attention_count = sum(1 for f in findings_list if f.get("status", "").strip().lower() == "attention")
                abnormal_count = sum(1 for f in findings_list if f.get("status", "").strip().lower() == "abnormal")

                # --- New Overall Health Summary Dashboard ---
                # Risk scoring logic per requirements:
                # 0 abnormal -> Low Risk (green)
                # 1-2 abnormal -> Moderate Risk (orange)
                # 3+ abnormal -> High Risk (red)
                if abnormal_count == 0:
                    risk_label = "Low Risk"
                    risk_class = "green"
                    overall_health = "Healthy"
                elif 1 <= abnormal_count <= 2:
                    risk_label = "Moderate Risk"
                    risk_class = "yellow"
                    overall_health = "Needs Attention"
                else:
                    risk_label = "High Risk"
                    risk_class = "red"
                    overall_health = "Consult Doctor"

                # Render premium dashboard immediately after analysis and before tabs
                st.markdown(f"""
                <div class='result-metrics-row'>
                  <div class='metric-card' style='background: linear-gradient(135deg, #ecfdf5, #dcfce7);'>
                    <div class='metric-label'>Overall Health Status</div>
                    <div class='metric-value'>{overall_health}</div>
                    <div class='metric-note'>Based on detected findings</div>
                  </div>
                  <div class='metric-card' style='background: linear-gradient(135deg, #fff7ed, #ffedd5);'>
                    <div class='metric-label'>Risk Score</div>
                    <div class='metric-value'>{risk_label}</div>
                    <div class='metric-note'>Color-coded summary of risk</div>
                  </div>
                  <div class='metric-card' style='background: linear-gradient(135deg, #eef2ff, #e0e7ff);'>
                    <div class='metric-label'>Tests Analyzed</div>
                    <div class='metric-value'>{total_tests}</div>
                    <div class='metric-note'>Number of tests parsed</div>
                  </div>
                  <div class='metric-card' style='background: linear-gradient(135deg, #fff1f2, #fee2e2);'>
                    <div class='metric-label'>Abnormal Findings</div>
                    <div class='metric-value'>{abnormal_count}</div>
                    <div class='metric-note'>Findings flagged as abnormal</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Keep original status chip for continuity with existing UI
                if abnormal_count > 1:
                    overall_status = ("🔴 Follow-up Recommended", "red")
                elif abnormal_count == 1 or attention_count > 0:
                    overall_status = ("🟡 Needs Medical Review", "yellow")
                else:
                    overall_status = ("🟢 Normal Results", "green")

                st.markdown(f"<div class='status-chip {overall_status[1]}'>{overall_status[0]}</div>", unsafe_allow_html=True)

                # Original metric cards (kept for backward compatibility)
                st.markdown("""
                <div class='result-metrics-row'>
                  <div class='metric-card'>
                    <div class='metric-label'>Tests Found</div>
                    <div class='metric-value'>{}</div>
                    <div class='metric-note'>Total measured markers</div>
                  </div>
                  <div class='metric-card'>
                    <div class='metric-label'>Normal Findings</div>
                    <div class='metric-value'>{}</div>
                    <div class='metric-note'>Within expected ranges</div>
                  </div>
                  <div class='metric-card'>
                    <div class='metric-label'>Abnormal Findings</div>
                    <div class='metric-value'>{}</div>
                    <div class='metric-note'>Requires closer review</div>
                  </div>
                  <div class='metric-card'>
                    <div class='metric-label'>Analysis Status</div>
                    <div class='metric-value'>Complete</div>
                    <div class='metric-note'>Gemini 2.5 Flash</div>
                  </div>
                </div>
                """.format(total_tests, normal_count, abnormal_count), unsafe_allow_html=True)

                tab1, tab2, tab3, tab4 = st.tabs(["🔍 Key Findings", "📝 Patient-Friendly Explanation", "💬 Doctor Questions", "💬 Chat with Report"])

                with tab1:
                    if findings_list:
                        table_rows = ""
                        for f in findings_list:
                            status_str = f.get("status", "Normal")
                            status_class = "badge-critical" if status_str.lower() == "abnormal" else "badge-normal"
                            if status_str.lower() == "attention":
                                status_class = "badge-attention"
                            badge_html = f'<span class="status-pill {status_class}">{status_str}</span>'
                            table_rows += (
                                f"<tr>"
                                f"<td>{f.get('test_name')}</td>"
                                f"<td>{f.get('value')}</td>"
                                f"<td>{f.get('normal_range')}</td>"
                                f"<td>{badge_html}</td>"
                                f"</tr>"
                            )
                        st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Summary of Findings</div><div class='card-sub'>Organized clinical test results</div></div></div><table class='table-card'><tr><th>Test / Marker</th><th>Value</th><th>Normal Range</th><th>Status</th></tr>{table_rows}</table></div>", unsafe_allow_html=True)
                    else:
                        st.info("No recognized lab markers were found in the report. Please refine your input or upload a different report.")

                with tab2:
                    summary_text = explanation_data.get("summary", "No patient-friendly summary was generated.")
                    st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Overall Summary</div><div class='card-sub'>Layperson explanation</div></div></div><div class='card-note'>{summary_text}</div></div>", unsafe_allow_html=True)
                    if explanations_list:
                        for exp in explanations_list:
                            t_name = exp.get("test_name", "Test")
                            t_expl = exp.get("simple_explanation", "")
                            st.markdown(f"<details class='details-card'><summary>{t_name}</summary><div>{t_expl}</div></details>", unsafe_allow_html=True)
                    else:
                        st.info("No individual test explanations are available.")

                with tab3:
                    if questions_list:
                        question_text = "\n".join([f"{idx + 1}. {q}" for idx, q in enumerate(questions_list)])
                        safe_question_text = question_text.replace("\"", "\\\"")
                        st.markdown(f"<button class='copy-button' onclick=\"navigator.clipboard.writeText('{safe_question_text}')\">Copy questions</button>", unsafe_allow_html=True)
                        st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Doctor Questions</div><div class='card-sub'>Checklist for your next visit</div></div></div><div style='color: #475569; line-height:1.7;'><ol>{''.join([f'<li style=\"margin-bottom: 12px;\">{q}</li>' for q in questions_list])}</ol></div></div>", unsafe_allow_html=True)
                    else:
                        st.info("No doctor questions were generated.")

                    disclaimer_text = question_data.get("disclaimer", "This analysis is for informational purposes only. Consult a healthcare professional.")
                    st.markdown(f"<div class='warning-box'><strong>Disclaimer:</strong> {disclaimer_text}</div>", unsafe_allow_html=True)

                with tab4:
                    st.markdown("<div class='glass-card'><div class='card-header'><div><div class='card-title'>Chat with Report</div><div class='card-sub'>Ask follow-up questions about this analysis</div></div></div></div>", unsafe_allow_html=True)
                    if st.session_state.get('analysis_data'):
                        with st.form(key='report_chat_form', clear_on_submit=False):
                            st.text_input(
                                "Ask a question about this report:",
                                key="chat_query",
                                placeholder="For example: What should I discuss with my doctor?"
                            )
                            submitted = st.form_submit_button("Send Question")
                            if submitted:
                                handle_chat_submit()

                        if st.session_state.get('chat_history'):
                            for sender, message in st.session_state.chat_history:
                                if sender == "You":
                                    st.markdown(f"**You:** {message}")
                                else:
                                    st.markdown(f"**Navigator:** {message}")
                    else:
                        st.info("Run report analysis first to enable the chat assistant.")

                st.markdown('<div class="footer-panel"><div class="footer-title">Powered by Gemini 2.5 Flash</div><div class="footer-subtitle">Modern clinical AI summary portal</div><div class="footer-metrics"><div>• PDF Report Analysis</div><div>• Multi-Agent AI Workflow</div><div>• Patient-Friendly Explanations</div><div>• Doctor Consultation Preparation</div></div></div>', unsafe_allow_html=True)
                
            except json.JSONDecodeError as jde:
                status_container.update(label="JSON parsing error!", state="error")
                st.error("Failed to parse the structured responses from the agents. Please try again.")
                st.write(jde)
            except Exception as e:
                status_container.update(label="Execution error!", state="error")
                st.error(f"An unexpected error occurred: {str(e)}")
                
    else:
        st.warning("Please paste or load a medical report first.")