from app.utils import generate_embeddings_for_html_files_with_chunking

if __name__ == "__main__":
    DATA_DIR = "./data"
    OUTPUT_FILE = "knowledge_base_embeddings_chunked.json"

    # Generate embeddings for the HTML files
    generate_embeddings_for_html_files_with_chunking(DATA_DIR, OUTPUT_FILE)
