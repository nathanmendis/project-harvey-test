import os
import requests
from bs4 import BeautifulSoup
import pdfminer.high_level
import docx
from django.conf import settings
from core.models.policy import Policy, PolicyChunk
from core.vector_store import get_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PolicyIndexer:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    def index_policy(self, policy_id):
        try:
            policy = Policy.objects.get(id=policy_id)
            policy.status = 'indexing'
            policy.save()

            text = self._extract_text(policy)
            if not text:
                raise ValueError("No text extracted from policy source")

            # Clear existing chunks
            policy.chunks.all().delete()

            chunks = self.text_splitter.split_text(text)
            
            # Prepare for vector store
            texts = []
            metadatas = []
            
            for i, chunk_text in enumerate(chunks):
                # Save to DB
                PolicyChunk.objects.create(
                    policy=policy,
                    chunk_index=i,
                    text=chunk_text,
                    metadata={"source": policy.title}
                )
                
                texts.append(chunk_text)
                metadatas.append({
                    "source": policy.title,
                    "policy_id": str(policy.id),
                    "chunk_index": i,
                    "type": "policy"
                })

            # Add to Vector Store
            self.vector_store.add_documents(texts, metadatas)

            policy.status = 'indexed'
            policy.save()
            return True

        except Exception as e:
            print(f"Indexing failed: {e}")
            if policy:
                policy.status = 'failed'
                policy.save()
            return False

    def _extract_text(self, policy):
        if policy.source_type == 'url':
            return self._extract_from_url(policy.external_url)
        elif policy.source_type == 'upload':
            return self._extract_from_file(policy.uploaded_file)
        return ""

    def _extract_from_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            print(f"URL extraction failed: {e}")
            return ""

    def _extract_from_file(self, file_field):
        try:
            file_path = file_field.path
            ext = os.path.splitext(file_path)[1].lower()

            if ext == '.pdf':
                return pdfminer.high_level.extract_text(file_path)
            elif ext == '.docx':
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return "" # Unsupported format
        except Exception as e:
            print(f"File extraction failed: {e}")
            return ""
