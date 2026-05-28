from google import genai

client = genai.Client(api_key='AIzaSyAYWpS96fVWH38zeKcJmbeaez9V6Y5D_wU')

# 直接體驗最新一代的 3.5 Flash 
response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents='靜宜資管有什麼特色?',
)

print(response.text)