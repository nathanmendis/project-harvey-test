print("Importing transformers...")
try:
    import transformers
    print(f"Transformers version: {transformers.__version__}")
    from langchain_huggingface import HuggingFaceEmbeddings
    print("HuggingFaceEmbeddings imported successfully")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
