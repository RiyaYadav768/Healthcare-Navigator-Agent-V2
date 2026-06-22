import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

prompt = """
Analyze the following sample medical report and structure your response in JSON format with these exact keys:
1. "summary": A clear, simple summary of the report in plain English.
2. "findings": A list of key findings, explaining any abnormal values.
3. "questions": A list of recommended questions for the patient to ask their doctor.
4. "disclaimer": A standard medical disclaimer.

Sample medical report:
Patient has low hemoglobin of 10.2 g/dL. White blood cell count is normal at 6,500. Thyroid stimulating hormone (TSH) is slightly elevated at 5.1 mIU/L.
"""

response = model.generate_content(
    prompt,
    generation_config={"response_mime_type": "application/json"}
)

print(response.text)
try:
    data = json.loads(response.text)
    print("SUCCESSFULLY PARSED JSON:")
    print(data)
except Exception as e:
    print("FAILED TO PARSE JSON:", e)
