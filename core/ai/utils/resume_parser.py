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
        Falls back to rule-based regex parsing if GROQ_API_KEY is not configured.
        """
        import os
        import re
        
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            logger.info("GROQ_API_KEY not found. Using rule-based regex resume parser.")
            return self.extract_info_rule_based(text)

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
            logger.error(f"Failed to extract info via LLM: {e}. Falling back to rule-based.")
            return self.extract_info_rule_based(text)

    def extract_info_rule_based(self, text):
        """
        Regex and heuristic based parsing for offline/no-LLM extraction.
        """
        import re
        
        # 1. Extract Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        email = email_match.group(0) if email_match else ""
        
        # 2. Extract Name Heuristic (first few short lines)
        name = ""
        for line in text.split('\n'):
            line_strip = line.strip()
            if line_strip and len(line_strip.split()) <= 4:
                if not any(w in line_strip.lower() for w in ['resume', 'curriculum', 'vitae', 'cv', 'page', 'email', 'phone', 'contact']):
                    name = line_strip
                    break

        # 3. Extract Skills Section
        header_patterns = [
            r'(?:technical\s+)?skills',
            r'key\s+skills',
            r'core\s+skills',
            r'technologies',
            r'expertise',
            r'skills\s+&\s+expertise',
            r'skills\s+and\s+tools',
            r'programming\s+languages'
        ]
        
        next_headers = [
            r'experience',
            r'work\s+experience',
            r'employment\s+history',
            r'professional\s+experience',
            r'education',
            r'projects',
            r'academic\s+projects',
            r'personal\s+projects',
            r'certifications',
            r'awards',
            r'languages',
            r'interests',
            r'publications',
            r'summary',
            r'profile',
            r'contact'
        ]
        
        text_lower = text.lower()
        skills_text = ""
        
        for pattern in header_patterns:
            match = re.search(r'\b' + pattern + r'\b', text_lower)
            if match:
                start_idx = match.end()
                # Find where the next section starts
                end_idx = len(text)
                for next_pat in next_headers:
                    next_match = re.search(r'\b' + next_pat + r'\b', text_lower[start_idx:])
                    if next_match:
                        match_pos = start_idx + next_match.start()
                        if match_pos < end_idx:
                            end_idx = match_pos
                
                skills_section = text[start_idx:end_idx].strip()
                if skills_section:
                    skills_text = skills_section
                    break
        
        skills = []
        if skills_text:
            # Clean separators and split
            cleaned = re.sub(r'[\r\n\t•\-\*·|]', ',', skills_text)
            raw_skills = re.split(r'[,;]', cleaned)
            for s in raw_skills:
                s_clean = s.strip()
                # Keep words/phrases of reasonable length (2 to 50 chars)
                if s_clean and 2 <= len(s_clean) <= 50:
                    if not any(phrase in s_clean.lower() for phrase in ['resume', 'curriculum', 'page', 'university', 'college', 'responsible for', 'experience']):
                        skills.append(s_clean)

        return {
            "name": name,
            "email": email,
            "skills": skills
        }

