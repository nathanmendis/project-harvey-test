import os
from langchain_postgres import PGVector
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
        
        # Construct connection string from Django settings
        db_config = settings.DATABASES['default']
        self.connection_string = (
            f"postgresql+psycopg://{db_config['USER']}:{db_config['PASSWORD']}"
            f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
        )
        
        self.collection_name = "harvey_vectors"
        
        # Initialize PGVector
        self.db = PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
        )

    def create_index(self, texts, metadatas):
        """Creates a new index (drops existing table/collection if possible or just adds)"""
        # PGVector doesn't have a direct "delete_collection" method in the same way
        # But we can drop the table if we really want to start fresh, or just add.
        # For now, we'll just add, or we could drop the table via SQL if needed.
        # To keep it simple and safe, we just add.
        if texts:
            self.db.add_texts(texts, metadatas=metadatas)

    def add_documents(self, texts, metadatas):
        """Adds documents to existing index"""
        if texts:
            self.db.add_texts(texts, metadatas=metadatas)



    def similarity_search(self, query, k=3):
        return self.db.similarity_search(query, k=k)

def get_vector_store():
    return VectorStore()
