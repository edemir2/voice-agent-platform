# ingest_data.py
import os
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

print("Starting data ingestion process for all sources...")

# Load environment variables from .env file
load_dotenv()

# --- 1. Define All Data Sources ---
# List all the JSON files you want to include in the knowledge base.
data_directory = './voice_agent_service/clients/sonmez/data/'
json_files = [
    os.path.join(data_directory, 'structured_tent_products.json'),
    os.path.join(data_directory, 'scraped_accessories.json'),
    os.path.join(data_directory, 'FAQ.json')
]

# --- 2. Load and Combine Documents from All Files ---
all_documents = []
for file_path in json_files:
    if os.path.exists(file_path):
        loader = JSONLoader(
            file_path=file_path,
            jq_schema='.',
            text_content=False
        )
        documents = loader.load()
        all_documents.extend(documents)
        print(f"Loaded {len(documents)} documents from {os.path.basename(file_path)}.")
    else:
        print(f"Warning: File not found at {file_path}. Skipping.")

print(f"\nTotal documents loaded from all sources: {len(all_documents)}")

# --- 3. Split Documents into Chunks ---
# This breaks down all the combined data into smaller, manageable pieces.
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunked_documents = text_splitter.split_documents(all_documents)
print(f"Split total documents into {len(chunked_documents)} chunks.")

# --- 4. Embed and Store in Pinecone ---
# This converts the text chunks into vectors and uploads them.
# Note: This will add the new data to your existing index.
print("Embedding documents and uploading to Pinecone...")
PineconeVectorStore.from_documents(
    documents=chunked_documents,
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
    index_name="sonmez-products" # Your Pinecone index name
)

print("✅ Ingestion complete! Your knowledge base is now updated with all data sources.")