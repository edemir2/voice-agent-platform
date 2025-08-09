# ingest_data.py
import os
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

print("Starting data ingestion process for all sources...")

# Developer's Note: As a first step, We're loading the environment variables. This is crucial
# because the script needs API keys for both OpenAI (for embeddings) and Pinecone (for storage).
load_dotenv()

# Developer's Note: We're centralizing the paths to our data sources here. This makes it
# easy to add or remove knowledge files in the future without changing the core logic.
# The os.path.join ensures the file paths are correct regardless of the operating system.
data_directory = './voice_agent_service/clients/sonmez/data/'
json_files = [
    os.path.join(data_directory, 'structured_tent_products.json'),
    os.path.join(data_directory, 'scraped_accessories.json'),
    os.path.join(data_directory, 'FAQ.json')
]

# Developer's Note: The goal here is to gather all pieces of information from our various
# files into a single list. I'm using LangChain's JSONLoader because it's specifically
# designed to parse JSON files into a standardized 'Document' format that the rest of
# the RAG pipeline expects. The jq_schema='.' is a simple way to tell the loader to
# extract all content from each JSON object.
all_documents = []
for file_path in json_files:
    if os.path.exists(file_path):
        loader = JSONLoader(
            file_path=file_path,
            jq_schema='.',
            text_content=False  # I set this to False to preserve the original structure as metadata.
        )
        documents = loader.load()
        all_documents.extend(documents)
        print(f"Loaded {len(documents)} documents from {os.path.basename(file_path)}.")
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