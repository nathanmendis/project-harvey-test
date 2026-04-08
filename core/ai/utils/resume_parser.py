import os
from pypdf import PdfReader
from docx import Document
import json
import logging
from langchain_groq import ChatGroq

logger = logging.getLogger("harvey")

class ResumeParser:
    def parse(self, file_path):
        """
        Parses a resume file (PDF or DOCX) and extracts text.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._parse_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _parse_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise ValueError(f"Error parsing PDF: {e}")

    def _parse_docx(self, file_path):
        try:
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            raise ValueError(f"Error parsing DOCX: {e}")

    def extract_info(self, text):
        """
        Uses LLM to extract Name, Email, and Skills from resume text.
        """
        import os
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return {"name": "", "email": "", "skills": []}

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=groq_key)
        
        prompt = f"""
        Extract the following information from the resume text provided below:
        1. Full Name
        2. Email Address
        3. A list of key technical skills (comma-separated)

        Return the result ONLY as a JSON object with the keys "name", "email", and "skills".
        If a field is missing, use null.

        Resume Text:
        {text[:4000]}
        """

        try:
            response = llm.invoke(prompt)
            # Clean response to ensure it's valid JSON
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(content)
            return {
                "name": data.get("name") or "",
                "email": data.get("email") or "",
                "skills": data.get("skills") if isinstance(data.get("skills"), list) else [s.strip() for s in str(data.get("skills")).split(",")] if data.get("skills") else []
            }
        except Exception as e:
            logger.error(f"Failed to extract info from resume text: {e}")
            return {"name": "", "email": "", "skills": []}
