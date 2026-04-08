import os
import sys

# Add current directory to path so we can import core
sys.path.append(os.getcwd())

# Setup Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')
django.setup()

from core.ai.utils.resume_parser import ResumeParser

def test_parse():
    parser = ResumeParser()
    try:
        text = parser.parse("resume.pdf")
        print("--- START OF TEXT ---")
        print(text)
        print("--- END OF TEXT ---")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parse()
