import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from django.conf import settings

class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Use a lightweight local model
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.index_path = "faiss_index"
        self.db = self._load_local()

    def _load_local(self):
        if os.path.exists(self.index_path):
            try:
                return FAISS.load_local(
                    self.index_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Failed to load index: {e}")
        return None

    def create_index(self, texts, metadatas):
        """Creates a new index from scratch"""
        self.db = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
        self.save_local()

    def add_documents(self, texts, metadatas):
        """Adds documents to existing index or creates new one"""
        if self.db:
            self.db.add_texts(texts, metadatas=metadatas)
        else:
            self.create_index(texts, metadatas)
        self.save_local()

    def save_local(self):
        if self.db:
            self.db.save_local(self.index_path)

    def similarity_search(self, query, k=3):
        if not self.db:
            return []
        return self.db.similarity_search(query, k=k)

def get_vector_store():
    return VectorStore()
