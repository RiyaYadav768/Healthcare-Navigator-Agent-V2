import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

sample_report = (
    "CBC Report:\n"
    "- Hemoglobin: 10.5 g/dL (Normal range: 12.0 - 15.5 g/dL)\n"
    "- Hematocrit: 32% (Normal range: 37% - 48%)\n"
    "- White Blood Cells: 6,000 /mcL (Normal range: 4,500 - 11,000 /mcL)\n"
    "- Platelets: 250,000 /mcL (Normal range: 150,000 - 450,000 /mcL)"
)

prompt = f"""
You are a multi-agent clinical translation system consisting of three virtual agents. 
Analyze the following medical report and perform the tasks of each agent sequentially:
---
{sample_report}
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

print("Sending optimized call request...")
response = model.generate_content(
    prompt,
    generation_config={"response_mime_type": "application/json"}
)

print("Received Response:")
print(response.text)

# Parse response
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

try:
    data = clean_and_parse_json(response.text)
    print("\nSUCCESSFULLY PARSED UNIFIED JSON!")
    print(f"Analysis Findings Count: {len(data.get('analysis', {}).get('findings', []))}")
    print(f"Explanation Summary Length: {len(data.get('explanation', {}).get('summary', ''))}")
    print(f"Doctor Questions Count: {len(data.get('doctor_questions', {}).get('questions', []))}")
except Exception as e:
    print("\nFAILED TO PARSE JSON:", e)
