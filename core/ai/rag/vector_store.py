import os
from django.conf import settings

class VectorStore:
    _embeddings_instance = None

    def __init__(self):
        self._initialize()

    @classmethod
    def get_embeddings(cls):
        from langchain_huggingface import HuggingFaceEmbeddings
        if cls._embeddings_instance is None:
            cls._embeddings_instance = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'}
            )

        return cls._embeddings_instance

    def _initialize(self):
        from langchain_postgres import PGVector
        
        # Use cached embeddings
        self.embeddings = self.get_embeddings()
        
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



    def delete_by_policy_id(self, policy_id):
        """Deletes all chunks for a specific policy from the vector store."""
        try:
            from sqlalchemy import text, create_engine
            # create a temporary engine to execute the deletion
            engine = create_engine(self.connection_string)
            sql = text("DELETE FROM langchain_pg_embedding WHERE cmetadata->>'policy_id' = :policy_id")
            with engine.connect() as conn:
                conn.execute(sql, {"policy_id": str(policy_id)})
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting vectors for policy {policy_id}: {e}")
            return False

    def delete_by_candidate_id(self, candidate_id):
        """Deletes all vectors for a specific candidate from the vector store."""
        try:
            from sqlalchemy import text, create_engine
            engine = create_engine(self.connection_string)
            sql = text("DELETE FROM langchain_pg_embedding WHERE cmetadata->>'candidate_id' = :candidate_id")
            with engine.connect() as conn:
                conn.execute(sql, {"candidate_id": str(candidate_id)})
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting vectors for candidate {candidate_id}: {e}")
            return False

    def delete_by_job_id(self, job_id):
        """Deletes all vectors for a specific job role from the vector store."""
        try:
            from sqlalchemy import text, create_engine
            engine = create_engine(self.connection_string)
            sql = text("DELETE FROM langchain_pg_embedding WHERE cmetadata->>'job_id' = :job_id")
            with engine.connect() as conn:
                conn.execute(sql, {"job_id": str(job_id)})
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting vectors for job {job_id}: {e}")
            return False

    def delete_all(self):
        """Clears all vectors in the collection."""
        try:
             # Dropping the collection is the cleanest way to clear everything
             self.db.delete_collection()
             # Re-initialize to recreate the collection if needed
             self._initialize()
             return True
        except Exception as e:
             # Fallback if delete_collection is not available or fails
             print(f"Error deleting collection: {e}")
             return False

    def similarity_search(self, query, k=3, **kwargs):
        return self.db.similarity_search(query, k=k, **kwargs)

_vector_store_instance = None

def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
