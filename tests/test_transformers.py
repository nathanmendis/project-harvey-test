from django.test import TestCase

class TestTransformersSanity(TestCase):
    def test_imports(self):
        """Verify transformers and HuggingFaceEmbeddings can be imported."""
        import transformers
        self.assertIsNotNone(transformers.__version__)
        from langchain_huggingface import HuggingFaceEmbeddings
        self.assertIsNotNone(HuggingFaceEmbeddings)
