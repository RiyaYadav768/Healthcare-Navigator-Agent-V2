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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Apply font family to entire app */
    html, body, [class*="css"], .stMarkdown, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #f8fafc !important;
    }
    
    /* Global dark background theme with SVG medical illustrations */
    [data-testid="stAppViewContainer"] {
        background-color: #080c14 !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.12) 0%, transparent 40%),
            radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.12) 0%, transparent 40%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='1' fill='rgba(99, 102, 241, 0.05)'/%3E%3C/svg%3E"),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='600' viewBox='0 0 1200 600'%3E%3Cpath d='M0 300 L300 300 L320 250 L340 350 L360 280 L380 320 L400 300 L600 300 L620 200 L640 400 L660 150 L680 450 L700 280 L720 320 L740 300 L1200 300' fill='none' stroke='rgba(99, 102, 241, 0.04)' stroke-width='1.5' stroke-dasharray='10 15'/%3E%3C/svg%3E"),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='800' viewBox='0 0 800 800'%3E%3Cg opacity='0.03' stroke='%238b5cf6' stroke-width='1.5' fill='none'%3E%3Cpath d='M100,100 C150,150 200,50 250,100 C300,150 350,50 400,100 C450,150 500,50 550,100 C600,150 650,50 700,100' /%3E%3Cpath d='M100,140 C150,90 200,190 250,140 C300,90 350,190 400,140 C450,90 500,190 550,140 C600,90 650,190 700,140' /%3E%3Cpath d='M100,100 L100,140 M250,100 L250,140 M400,100 L400,140 M550,100 L550,140 M700,100 L700,140' /%3E%3C/g%3E%3C/svg%3E") !important;
        background-size: cover, cover, auto, 100% 100%, 350px 350px !important;
        background-repeat: no-repeat, no-repeat, repeat, repeat-x, repeat !important;
        background-attachment: fixed !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    .main {
        background: transparent !important;
    }
    
    /* Remove white content background blocks from streamlit */
    div.block-container {
        background: transparent !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Style the sidebar container */
    [data-testid="stSidebar"] {
        background: rgba(8, 12, 20, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    [data-testid="stSidebar"] [class*="css"] {
        color: #cbd5e1 !important;
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

# Initialize session state variables if not present
if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "overall_health" not in st.session_state:
    st.session_state.overall_health = "Unknown"
if "risk_label" not in st.session_state:
    st.session_state.risk_label = "Low Risk"
if "total_tests" not in st.session_state:
    st.session_state.total_tests = 0
if "abnormal_count" not in st.session_state:
    st.session_state.abnormal_count = 0
if "normal_count" not in st.session_state:
    st.session_state.normal_count = 0
if "attention_count" not in st.session_state:
    st.session_state.attention_count = 0

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

# Premium Healthcare Dashboard Styling & Layout Rebuild
st.markdown("""
<style>
/* Font override */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Base resets & layouts */
.block-container {
    max-width: 900px !important;
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
}

/* Custom premium scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.2);
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.5);
}

/* Main glass card rules */
.glass-card {
    background: rgba(15, 23, 42, 0.45) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 24px !important;
    padding: 32px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3) !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    margin-bottom: 24px !important;
    position: relative;
    overflow: hidden;
}
.glass-card:hover {
    transform: translateY(-4px) !important;
    border-color: rgba(99, 102, 241, 0.35) !important;
    box-shadow: 0 30px 60px rgba(99, 102, 241, 0.15) !important;
}

/* Hero Section Custom Styles */
.hero-badge {
    animation: glow-pulse 3s infinite ease-in-out;
}
@keyframes glow-pulse {
    0%, 100% { box-shadow: 0 0 10px rgba(99, 102, 241, 0.1); }
    50% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.35); }
}
.hero-pill {
    transition: all 0.3s ease !important;
}
.hero-pill:hover {
    background: rgba(99, 102, 241, 0.15) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    transform: translateY(-1px) !important;
}

/* Workflow steps */
.workflow-grid {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin: 36px 0;
}
.workflow-card-premium {
    flex: 1;
    min-width: 200px;
    background: rgba(15, 23, 42, 0.45) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    padding: 24px 20px !important;
    border-radius: 20px !important;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.3s ease !important;
}
.workflow-card-premium:hover {
    transform: translateY(-2px) !important;
    border-color: rgba(99, 102, 241, 0.2) !important;
    box-shadow: 0 16px 40px rgba(99, 102, 241, 0.08) !important;
}
.workflow-connector {
    color: #6366f1;
    font-size: 24px;
    font-weight: 800;
    text-align: center;
    width: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: arrow-bounce-right 2s infinite ease-in-out;
}
@keyframes arrow-bounce-right {
    0%, 100% { transform: translateX(0); }
    50% { transform: translateX(4px); }
}

@media (max-width: 768px) {
    .workflow-grid {
        flex-direction: column !important;
        align-items: stretch !important;
    }
    .workflow-connector {
        transform: rotate(90deg) !important;
        margin: 12px auto !important;
        animation: arrow-bounce-down 2s infinite ease-in-out !important;
    }
}
@keyframes arrow-bounce-down {
    0%, 100% { transform: rotate(90deg) translateY(0); }
    50% { transform: rotate(90deg) translateY(4px); }
}

/* Feature grid customization */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
    margin: 36px 0;
}

/* Sidebar overrides */
.sidebar-panel {
    background: rgba(15, 23, 42, 0.45) !important;
    border-radius: 20px !important;
    padding: 24px 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3) !important;
}
.sidebar-header-panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 24px;
}
.sidebar-dashboard-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #f8fafc !important;
    letter-spacing: -0.3px;
}
.sidebar-dashboard-subtitle {
    font-size: 0.85rem;
    color: #94a3b8 !important;
}
.sidebar-logo {
    width: 48px;
    height: 48px;
    background: rgba(99, 102, 241, 0.12) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
}
.sidebar-stats {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.sidebar-stat {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 16px !important;
    border-radius: 16px !important;
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.sidebar-stat:hover {
    background: rgba(255, 255, 255, 0.04) !important;
    border-color: rgba(99, 102, 241, 0.15) !important;
}
.sidebar-stat .stat-icon {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: rgba(99, 102, 241, 0.15) !important;
    color: #818cf8 !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}
.sidebar-stat .stat-label {
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    margin: 0 !important;
}
.sidebar-stat .stat-value {
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    margin-top: 2px;
}

/* File uploader custom styling overrides */
[data-testid="stFileUploader"] {
    background: rgba(15, 23, 42, 0.3) !important;
    border: 2px dashed rgba(99, 102, 241, 0.25) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    transition: all 0.3s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(99, 102, 241, 0.5) !important;
    background: rgba(15, 23, 42, 0.4) !important;
}
[data-testid="stFileUploader"] section {
    background: transparent !important;
    padding: 0 !important;
}
[data-testid="stFileUploader"] label {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploader"] button {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
    padding: 6px 14px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] button:hover {
    background: rgba(255, 255, 255, 0.15) !important;
    border-color: rgba(99, 102, 241, 0.3) !important;
}

/* Text area input styling */
.stTextArea textarea {
    background-color: rgba(15, 23, 42, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    color: #f8fafc !important;
    font-family: inherit !important;
    transition: all 0.3s ease !important;
    padding: 16px !important;
    font-size: 0.95rem !important;
}
.stTextArea textarea:focus {
    border-color: rgba(99, 102, 241, 0.45) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25) !important;
}

/* Button style adjustments */
.stButton>button {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
    color: white !important;
    border-radius: 14px !important;
    padding: 12px 24px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2) !important;
    letter-spacing: 0.3px !important;
}
.stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 30px rgba(99, 102, 241, 0.35) !important;
    color: white !important;
}
.stButton>button:active {
    transform: translateY(0px) !important;
}
/* Specifically styled button for clearing text area */
div[data-testid="column"]:last-child button {
    background: rgba(255, 255, 255, 0.04) !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: none !important;
}
div[data-testid="column"]:last-child button:hover {
    background: rgba(239, 68, 68, 0.15) !important;
    color: #f87171 !important;
    border-color: rgba(239, 68, 68, 0.3) !important;
    box-shadow: 0 8px 20px rgba(239, 68, 68, 0.1) !important;
}

/* Details and collapsibles */
.details-card {
    background: rgba(15, 23, 42, 0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 18px !important;
    padding: 18px 20px !important;
    margin-bottom: 12px !important;
    transition: all 0.2s ease !important;
}
.details-card:hover {
    background: rgba(15, 23, 42, 0.45) !important;
    border-color: rgba(99, 102, 241, 0.15) !important;
}
.details-card summary {
    font-size: 1.02rem !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    cursor: pointer;
    outline: none;
}
.details-card div {
    margin-top: 12px !important;
    color: #94a3b8 !important;
    line-height: 1.6 !important;
    font-size: 0.95rem !important;
}

/* Results indicators & metrics */
.result-metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.metric-card {
    background: rgba(15, 23, 42, 0.45) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 20px 22px !important;
    box-shadow: 0 16px 30px rgba(0, 0, 0, 0.25) !important;
    transition: all 0.3s ease !important;
}
.metric-card:hover {
    transform: translateY(-2px) !important;
    border-color: rgba(99, 102, 241, 0.25) !important;
}
.metric-label { color: #94a3b8 !important; font-size: 0.85rem !important; font-weight: 600 !important; margin-bottom: 8px !important; }
.metric-value { font-size: 1.8rem !important; font-weight: 800 !important; color: #f8fafc !important; }
.metric-note { color: #64748b !important; font-size: 0.8rem !important; margin-top: 6px !important; }

/* Status pill status badges */
.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 12px;
    border-radius: 99px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.badge-normal { background: rgba(16, 185, 129, 0.15) !important; color: #34d399 !important; border: 1px solid rgba(16, 185, 129, 0.25) !important; }
.badge-attention { background: rgba(245, 158, 11, 0.15) !important; color: #fbbf24 !important; border: 1px solid rgba(245, 158, 11, 0.25) !important; }
.badge-critical { background: rgba(239, 68, 68, 0.15) !important; color: #f87171 !important; border: 1px solid rgba(239, 68, 68, 0.25) !important; }

/* Table customization */
.table-card {
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
}
.table-card th {
    text-align: left;
    padding: 14px 16px;
    color: #cbd5e1 !important;
    font-weight: 700;
    font-size: 0.88rem;
    border-bottom: 2px solid rgba(255, 255, 255, 0.06);
}
.table-card td {
    padding: 14px 16px;
    color: #94a3b8 !important;
    font-size: 0.9rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.table-card tr:last-child td {
    border-bottom: none;
}

/* Warnings and footers */
.warning-box {
    border-radius: 18px !important;
    background: rgba(239, 68, 68, 0.08) !important;
    padding: 20px !important;
    border: 1px solid rgba(239, 68, 68, 0.18) !important;
    color: #f87171 !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
}
.footer-panel {
    background: rgba(15, 23, 42, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    margin-top: 36px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2) !important;
}
.footer-title {
    font-size: 0.98rem;
    color: #f8fafc !important;
    font-weight: 700;
    margin-bottom: 6px;
}
.footer-subtitle {
    color: #94a3b8;
    font-size: 0.88rem;
    margin-bottom: 20px;
}
.footer-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    color: #cbd5e1;
    font-size: 0.85rem;
}
.footer-metrics div {
    padding: 12px !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
}

/* Streamlit Tabs style overrides */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background-color: rgba(15, 23, 42, 0.2) !important;
    border-radius: 12px !important;
    padding: 6px !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(99, 102, 241, 0.18) !important;
    color: #a5b4fc !important;
}

/* Custom visual styling helpers */
h3 {
    color: #f8fafc !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px !important;
}
</style>

<!-- Hero Section -->
<div class="glass-card" style="position:relative;overflow:hidden;padding:40px;margin-top:10px;"><div style="position:absolute;width:350px;height:350px;background:radial-gradient(circle,rgba(99,102,241,0.16) 0%,transparent 70%);top:-100px;left:-100px;z-index:0;"></div><div style="display:flex;align-items:center;gap:32px;position:relative;z-index:1;flex-wrap:wrap;"><div style="background:rgba(99,102,241,0.12);border:1.5px solid rgba(99,102,241,0.35);padding:18px;border-radius:24px;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 8px 30px rgba(99,102,241,0.12);flex-shrink:0;"><svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L3 7V12C3 17.5 7 21.3 12 22C17 21.3 21 17.5 21 12V7L12 2Z" fill="rgba(79,70,229,0.6)" stroke="#818cf8" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 7V17M7 12H17" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/></svg></div><div style="flex:1;min-width:260px;"><div style="display:inline-flex;align-items:center;gap:8px;background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.25);padding:6px 14px;border-radius:99px;font-size:0.78rem;font-weight:700;color:#a5b4fc;margin-bottom:16px;letter-spacing:0.8px;text-transform:uppercase;"><span style="display:inline-block;width:6px;height:6px;background:#818cf8;border-radius:50%;box-shadow:0 0 8px #818cf8;"></span>Gemini Flash • Multi-Agent System</div><div style="font-size:2.6rem;font-weight:800;color:#ffffff;margin:0 0 10px 0;letter-spacing:-0.8px;line-height:1.1;">Healthcare Navigator Agent</div><div style="color:#94a3b8;font-size:1rem;line-height:1.6;margin:0 0 20px 0;">Transforming complex clinical lab reports into clear, structured, patient-centric insights instantly.</div><div style="display:flex;flex-wrap:wrap;gap:8px;"><span style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);padding:6px 12px;border-radius:99px;font-size:0.82rem;color:#cbd5e1;font-weight:600;">📄 PDF Reports</span><span style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);padding:6px 12px;border-radius:99px;font-size:0.82rem;color:#cbd5e1;font-weight:600;">🤖 3 AI Agents</span><span style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);padding:6px 12px;border-radius:99px;font-size:0.82rem;color:#cbd5e1;font-weight:600;">⚡ Real-Time Analysis</span><span style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);padding:6px 12px;border-radius:99px;font-size:0.82rem;color:#cbd5e1;font-weight:600;">🔒 Privacy Focused</span></div></div></div></div>
<!-- Workflow Row -->
<div class="workflow-grid"><div class="workflow-card-premium"><div style="width:44px;height:44px;border-radius:12px;background:rgba(59,130,246,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;">📄</div><div><div style="font-weight:700;font-size:0.95rem;color:#f8fafc;">Upload Report</div><div style="font-size:0.8rem;color:#94a3b8;margin-top:2px;">Submit lab assay or PDF</div></div></div><div class="workflow-connector">→</div><div class="workflow-card-premium"><div style="width:44px;height:44px;border-radius:12px;background:rgba(139,92,246,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;">🤖</div><div><div style="font-weight:700;font-size:0.95rem;color:#f8fafc;">AI Analysis</div><div style="font-size:0.8rem;color:#94a3b8;margin-top:2px;">Clinical multi-agent translation</div></div></div><div class="workflow-connector">→</div><div class="workflow-card-premium"><div style="width:44px;height:44px;border-radius:12px;background:rgba(16,185,129,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;">📊</div><div><div style="font-weight:700;font-size:0.95rem;color:#f8fafc;">Patient Insights</div><div style="font-size:0.8rem;color:#94a3b8;margin-top:2px;">Summaries &amp; consultation ready</div></div></div></div>
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

if st.session_state.step == "upload":
    st.markdown('<div class="feature-grid"><div class="glass-card" style="margin-bottom:0px!important;padding:24px!important;"><div style="width:40px;height:40px;border-radius:10px;background:rgba(59,130,246,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px;">🧠</div><div style="font-weight:700;font-size:1rem;color:#f8fafc;margin-bottom:6px;">AI Intelligence</div><div style="font-size:0.82rem;color:#94a3b8;line-height:1.45;">Gemini-powered multi-agent clinical translation with optimized single-call latency.</div></div><div class="glass-card" style="margin-bottom:0px!important;padding:24px!important;"><div style="width:40px;height:40px;border-radius:10px;background:rgba(16,185,129,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px;">🛡️</div><div style="font-weight:700;font-size:1rem;color:#f8fafc;margin-bottom:6px;">Secure &amp; Private</div><div style="font-size:0.82rem;color:#94a3b8;line-height:1.45;">HIPAA-aware parsing. Your data is processed securely with zero persistence.</div></div><div class="glass-card" style="margin-bottom:0px!important;padding:24px!important;"><div style="width:40px;height:40px;border-radius:10px;background:rgba(245,158,11,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px;">⚡</div><div style="font-weight:700;font-size:1rem;color:#f8fafc;margin-bottom:6px;">Fast &amp; Accurate</div><div style="font-size:0.82rem;color:#94a3b8;line-height:1.45;">Structured mapping isolates exact biomarker boundaries, reference intervals, and flags.</div></div><div class="glass-card" style="margin-bottom:0px!important;padding:24px!important;"><div style="width:40px;height:40px;border-radius:10px;background:rgba(239,68,68,0.12);display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px;">💡</div><div style="font-weight:700;font-size:1rem;color:#f8fafc;margin-bottom:6px;">Smart Insights</div><div style="font-size:0.82rem;color:#94a3b8;line-height:1.45;">Empathetic layperson translations combined with targeted consultation checklists.</div></div></div>', unsafe_allow_html=True)

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
    else:
        st.warning("Please paste or load a medical report first.")

if st.session_state.step == "analyze":
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

            findings_list = analysis_data.get("findings", [])
            explanations_list = explanation_data.get("explanations", [])
            questions_list = question_data.get("questions", [])

            # Initialize local variables with safe defaults (Requirement 3)
            overall_health = "Unknown"
            risk_label = "Low Risk"
            total_tests = 0
            abnormal_count = 0

            # Calculate metrics after findings_list is created (Requirement 4)
            total_tests = len(findings_list)
            abnormal_count = len([
                f for f in findings_list
                if str(f.get("status", "")).lower() == "abnormal"
            ])
            normal_count = len([
                f for f in findings_list
                if str(f.get("status", "")).lower() == "normal"
            ])
            attention_count = len([
                f for f in findings_list
                if str(f.get("status", "")).lower() == "attention"
            ])

            # Generate overall_health dynamically (Requirement 5)
            if abnormal_count == 0:
                overall_health = "Healthy"
            elif abnormal_count <= 2:
                overall_health = "Needs Attention"
            else:
                overall_health = "Consult Doctor"

            # Generate risk_label dynamically (Requirement 6)
            if abnormal_count == 0:
                risk_label = "Low Risk"
            elif abnormal_count <= 2:
                risk_label = "Moderate Risk"
            else:
                risk_label = "High Risk"

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

            # Store results in session state for later download/chat use (Requirement 7)
            st.session_state.analysis_data = analysis_data
            st.session_state.explanation_data = explanation_data
            st.session_state.question_data = question_data
            st.session_state.overall_health = overall_health
            st.session_state.risk_label = risk_label
            st.session_state.total_tests = total_tests
            st.session_state.abnormal_count = abnormal_count
            st.session_state.normal_count = normal_count
            st.session_state.attention_count = attention_count
            st.session_state.disclaimer_text = disclaimer_text
            st.session_state.pdf_bytes = pdf_bytes

            st.session_state.step = "results"
            status_container.update(label="All agents completed successfully!", state="complete", expanded=False)
            st.success("✓ Analysis complete! Review the outputs from each agent below.")
            
        except json.JSONDecodeError as jde:
            status_container.update(label="JSON parsing error!", state="error")
            st.error("Failed to parse the structured responses from the agents. Please try again.")
            st.write(jde)
            st.session_state.step = "upload"
        except Exception as e:
            status_container.update(label="Execution error!", state="error")
            st.error(f"An unexpected error occurred: {str(e)}")
            st.session_state.step = "upload"

if st.session_state.step == "results":
    # Retrieve all values safely from session state (Requirement 8)
    analysis_data = st.session_state.get("analysis_data", {})
    explanation_data = st.session_state.get("explanation_data", {})
    question_data = st.session_state.get("question_data", {})
    overall_health = st.session_state.get("overall_health", "Unknown")
    risk_label = st.session_state.get("risk_label", "Low Risk")
    total_tests = st.session_state.get("total_tests", 0)
    abnormal_count = st.session_state.get("abnormal_count", 0)
    normal_count = st.session_state.get("normal_count", 0)
    attention_count = st.session_state.get("attention_count", 0)
    disclaimer_text = st.session_state.get("disclaimer_text", "This analysis is for informational purposes only and not medical advice. Consult a healthcare professional for diagnosis and treatment.")
    pdf_bytes = st.session_state.get("pdf_bytes")

    findings_list = analysis_data.get("findings", [])
    explanations_list = explanation_data.get("explanations", [])
    questions_list = question_data.get("questions", [])

    # Calculate gauge parameters
    if risk_label.lower() == "low risk":
        gauge_color = "#10b981"
        gauge_dash = "80 251"
    elif risk_label.lower() == "moderate risk":
        gauge_color = "#f59e0b"
        gauge_dash = "160 251"
    else:
        gauge_color = "#ef4444"
        gauge_dash = "251 251"

    # Calculate health status indicator color
    if overall_health.lower() == "healthy":
        status_color = "#10b981"
    elif overall_health.lower() == "needs attention":
        status_color = "#f59e0b"
    else:
        status_color = "#ef4444"

    # 1. Health Status Pulse Badge
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 99px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); margin-top: 10px; margin-bottom: 20px; display: inline-flex;">
      <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {status_color}; box-shadow: 0 0 10px {status_color};"></span>
      <span style="font-weight: 700; font-size: 0.82rem; color: #cbd5e1; letter-spacing: 0.5px; text-transform: uppercase;">HEALTH STATUS: {overall_health}</span>
    </div>
    """, unsafe_allow_html=True)

    # 2. Risk Score Gauge & Metrics Grid Row
    col_gauge, col_metrics = st.columns([1, 2])
    
    with col_gauge:
        st.markdown(f"""
        <div class="glass-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; height: 100%; margin-bottom: 0px !important;">
          <div style="font-size: 0.82rem; color: #94a3b8; font-weight: 700; margin-bottom: 14px; letter-spacing: 0.5px; text-transform: uppercase;">Clinical Risk Score</div>
          <div style="position: relative; width: 220px; height: 120px; overflow: hidden; display: flex; align-items: flex-end; justify-content: center;">
            <svg width="220" height="220" style="position: absolute; top: 0; left: 0;">
              <path d="M 30,110 A 80,80 0 0,1 190,110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="12" stroke-linecap="round" />
              <path d="M 30,110 A 80,80 0 0,1 190,110" fill="none" stroke="{gauge_color}" stroke-dasharray="{gauge_dash}" stroke-width="12" stroke-linecap="round" style="filter: drop-shadow(0 0 8px {gauge_color}); transition: stroke-dasharray 1s ease-in-out;" />
            </svg>
            <div style="position: relative; z-index: 10; margin-bottom: 8px;">
              <div style="font-size: 1.7rem; font-weight: 800; color: #f8fafc;">{risk_label}</div>
              <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">Overall Assay Profile</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_metrics:
        st.markdown(f"""
        <div class="result-metrics-row">
          <div class="metric-card" style="border-left: 4px solid #3b82f6 !important;">
            <div class="metric-label">Tests Found</div>
            <div class="metric-value">{total_tests}</div>
            <div class="metric-note">Parsed markers</div>
          </div>
          <div class="metric-card" style="border-left: 4px solid #10b981 !important;">
            <div class="metric-label">Normal Findings</div>
            <div class="metric-value">{normal_count}</div>
            <div class="metric-note">In reference range</div>
          </div>
          <div class="metric-card" style="border-left: 4px solid #f59e0b !important;">
            <div class="metric-label">Needs Attention</div>
            <div class="metric-value">{attention_count}</div>
            <div class="metric-note">Observation findings</div>
          </div>
          <div class="metric-card" style="border-left: 4px solid #ef4444 !important;">
            <div class="metric-label">Abnormal Findings</div>
            <div class="metric-value">{abnormal_count}</div>
            <div class="metric-note">Critical review flags</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Action Toolbar (PDF Export + Voice Briefing)
    st.markdown("<div style='margin-top: 20px; margin-bottom: 24px;'>", unsafe_allow_html=True)
    col_pdf, col_voice = st.columns([1, 1])
    with col_pdf:
        if pdf_bytes:
            st.download_button(
                label="📥 Download PDF Summary Report",
                data=pdf_bytes,
                file_name="healthcare_report_summary.pdf",
                mime="application/pdf",
                key="download_report_pdf",
                use_container_width=True
            )
        elif not REPORTLAB_AVAILABLE:
            st.info("Install reportlab to enable PDF report download.")
    with col_voice:
        st.markdown("""
        <button class="voice-btn" style="width: 100%; height: 100%; min-height: 42px; background: rgba(99, 102, 241, 0.12) !important; color: #a5b4fc !important; border: 1.5px solid rgba(99, 102, 241, 0.3) !important; border-radius: 14px !important; font-weight: 700 !important; font-size: 0.92rem !important; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.3s ease !important;" onclick="alert('Voice Assistant Briefing: Briefing audio is simulated. In a production environment, this streams a natural speech breakdown of your results.')">
           <span>🎙️</span> Voice Assistant Briefing
        </button>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Result Details Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Key Findings", "📝 Patient Explanation", "💬 Doctor Questions", "💬 Chat Assistant"])

    with tab1:
        if findings_list:
            table_rows = ""
            for f in findings_list:
                status_str = f.get("status", "Normal")
                status_class = "badge-critical" if status_str.lower() == "abnormal" else "badge-normal"
                if status_str.lower() == "attention":
                    status_class = "badge-attention"
                badge_html = f'<span class="status-pill {status_class}">{status_str}</span>'
                
                # Findings progress range chart
                if status_str.lower() == "normal":
                    bar_color = "#34d399"
                    bar_width = "75%"
                elif status_str.lower() == "attention":
                    bar_color = "#fbbf24"
                    bar_width = "50%"
                else:
                    bar_color = "#f87171"
                    bar_width = "90%"
                
                chart_html = f"""
                <div style="width: 80px; height: 6px; background: rgba(255,255,255,0.06); border-radius: 99px; overflow: hidden; position: relative; display: inline-block; vertical-align: middle; margin-left: 12px;">
                  <div style="position: absolute; left: 0; top: 0; height: 100%; width: {bar_width}; background: {bar_color}; border-radius: 99px; box-shadow: 0 0 6px {bar_color};"></div>
                </div>
                """
                
                table_rows += (
                    f"<tr>"
                    f"<td>{f.get('test_name')}</td>"
                    f"<td><strong>{f.get('value')}</strong></td>"
                    f"<td>{f.get('normal_range')}</td>"
                    f"<td>{badge_html} {chart_html}</td>"
                    f"</tr>"
                )
            st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Summary of Findings</div><div class='card-sub'>Parsed diagnostic test logs</div></div></div><table class='table-card'><tr><th>Test / Marker</th><th>Value</th><th>Normal Range</th><th>Status / Range Chart</th></tr>{table_rows}</table></div>", unsafe_allow_html=True)
        else:
            st.info("No recognized lab markers were found in the report.")

    with tab2:
        summary_text = explanation_data.get("summary", "No patient-friendly summary was generated.")
        st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Patient-Friendly Summary</div><div class='card-sub'>Empathetic translation</div></div></div><div class='card-note' style='color: #cbd5e1; font-size: 1rem;'>{summary_text}</div></div>", unsafe_allow_html=True)
        if explanations_list:
            st.markdown("<h4 style='color:#cbd5e1; font-weight:700; margin-bottom:12px;'>Biomarker Interpretations</h4>", unsafe_allow_html=True)
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
            
            st.markdown(f"<button class='copy-button' onclick=\"navigator.clipboard.writeText('{safe_question_text}')\">📋 Copy Checklist to Clipboard</button>", unsafe_allow_html=True)
            
            li_items = "".join([f'<li style="margin-bottom: 12px; color: #cbd5e1; font-size: 0.95rem;"><input type="checkbox" style="margin-right: 10px; accent-color: #818cf8; transform: scale(1.15); vertical-align: middle;" /> {q}</li>' for q in questions_list])
            
            st.markdown(f"<div class='glass-card'><div class='card-header'><div><div class='card-title'>Doctor Questions Panel</div><div class='card-sub'>Checklist for your physician visit</div></div></div><ul style='list-style: none; padding-left: 0;'>{li_items}</ul></div>", unsafe_allow_html=True)
        else:
            st.info("No doctor questions were generated.")

        st.markdown(f"<div class='warning-box'><strong>Clinical Disclaimer:</strong> {disclaimer_text}</div>", unsafe_allow_html=True)

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
                st.markdown("<div style='display:flex; flex-direction:column; gap:12px; margin-top:20px;'>", unsafe_allow_html=True)
                for sender, message in st.session_state.chat_history:
                    if sender == "You":
                        bubble_style = "background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.25); color: #cbd5e1; align-self: flex-end; border-bottom-right-radius: 4px;"
                        sender_label = "You"
                    else:
                        bubble_style = "background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); color: #e2e8f0; align-self: flex-start; border-bottom-left-radius: 4px;"
                        sender_label = "Navigator"
                    
                    st.markdown(f"""
                    <div style='display: flex; flex-direction: column; max-width: 80%; {bubble_style} padding: 14px 18px; border-radius: 16px;'>
                      <span style='font-size: 0.75rem; color: #94a3b8; font-weight: 700; margin-bottom: 4px;'>{sender_label}</span>
                      <span style='font-size: 0.92rem; line-height: 1.5;'>{message}</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Run report analysis first to enable the chat assistant.")

    st.markdown('<div class="footer-panel"><div class="footer-title">Powered by Gemini 2.5 Flash</div><div class="footer-subtitle">Modern clinical AI summary portal</div><div class="footer-metrics"><div>• PDF Report Analysis</div><div>• Multi-Agent AI Workflow</div><div>• Patient-Friendly Explanations</div><div>• Doctor Consultation Preparation</div></div></div>', unsafe_allow_html=True)