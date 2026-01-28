
import os
import django
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

load_dotenv()

def test_key():
    key = os.getenv("GOOGLE_API_KEY")
    print(f"Testing API Key: ...{key[-5:] if key else 'None'}")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=key
        )
        print("Sending request to Gemini...")
        resp = llm.invoke("Hello, are you online?")
        print(f"\nSUCCESS! Response: {resp.content}")
    except Exception as e:
        print(f"\nFAILURE: {e}")

if __name__ == "__main__":
    test_key()
