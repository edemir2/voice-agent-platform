# ingest_data.py
import os
import json
from dotenv import load_dotenv
from langchain_core.documents import Document 
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

print("Starting data ingestion process for all sources...")

# Developer's Note: As a first step, We're loading the environment variables. This is crucial
# because the script needs API keys for both OpenAI (for embeddings) and Pinecone (for storage).
load_dotenv()


# Flattens a dictionary of metadata, converting lists and dicts to JSON strings,
# which is a format compatible with Pinecone's metadata requirements.
def flatten_metadata(metadata: dict) -> dict:
    new_metadata = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            # Convert lists and dictionaries to a JSON string
            new_metadata[key] = json.dumps(value)
        elif value is not None:
            # Keep primitive types (string, int, float, bool) as they are
            new_metadata[key] = value
    return new_metadata


# Developer's Note: We're centralizing the paths to our data sources here. This makes it
# easy to add or remove knowledge files in the future without changing the core logic.
# The os.path.join ensures the file paths are correct regardless of the operating system.
data_directory = './voice_agent_service/clients/sonmez/data/'
json_files = [
    os.path.join(data_directory, 'structured_tent_products.json'),
    os.path.join(data_directory, 'scraped_accessories.json'),
    os.path.join(data_directory, 'FAQ.json')
]


# Developer's Note: Manually parsing JSON lists to create structured Documents.
# This approach ensures each JSON object is treated as a separate document.
# `page_content` is a stringified version for vector search, while the original
# structured `metadata` is preserved for the RAG model's context.

all_documents = []
for file_path in json_files:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                flat_metadata = flatten_metadata(item)
                doc = Document(
                    page_content=json.dumps(item, indent=2),
                    metadata=flat_metadata
                )
                all_documents.append(doc)
        print(f"Loaded {len(data)} documents from {os.path.basename(file_path)}.")
    else:
        print(f"Warning: File not found at {file_path}. Skipping.")

print(f"\nTotal documents loaded from all sources: {len(all_documents)}")

# Developer's Note: Language models have a limited context window. We can't feed them entire
# documents at once. The solution is to split our documents into smaller, overlapping chunks.
# I chose RecursiveCharacterTextSplitter because it's smart about trying to split text
# along natural boundaries (like paragraphs or sentences). The chunk_overlap ensures
# that context isn't lost at the edges of a split.
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunked_documents = text_splitter.split_documents(all_documents)
print(f"Split total documents into {len(chunked_documents)} chunks.")

# Developer's Note: This is the final and most important step of the ingestion process.
# 'PineconeVectorStore.from_documents' is a powerful LangChain function that handles three
# things in one command:
#   1. It calls the OpenAI API to convert each text chunk into a numerical vector (embedding).
#   2. It connects to our Pinecone index.
#   3. It uploads (or "upserts") each vector along with its corresponding text chunk.
# After this step, our knowledge base will be fully searchable.
print("Embedding documents and uploading to Pinecone...")
PineconeVectorStore.from_documents(
    documents=chunked_documents,
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
    index_name="sonmez-products"  # This must match the index name in your Pinecone account.
)

print("✅ Ingestion complete! Your knowledge base is now updated with all data sources.")