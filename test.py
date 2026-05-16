import os
import google.generativeai as genai

api_key = os.getenv("AIzaSyBAalR3h6XYm1HHUjXD47DpZ3i6G5H_9A0")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content(
    "Explain HPLC air bubble issue in pharma QA"
)

print(response.text)