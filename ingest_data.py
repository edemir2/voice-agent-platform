import os
import json
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import logging

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Flattens a dictionary of metadata, converting lists and dicts to JSON strings,
# which is a format compatible with Pinecone's metadata requirements.

def flatten_metadata(metadata: dict) -> dict:
    flat_meta = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            flat_meta[key] = json.dumps(value)
        elif value is not None:
            flat_meta[key] = value
    return flat_meta

def main():
    """Main ingestion function."""
    logging.info("Starting data ingestion process for all sources...")
    # Developer's Note: As a first step, We're loading the environment variables. This is crucial
    # because the script needs API keys for both OpenAI (for embeddings) and Pinecone (for storage).
    load_dotenv()

    data_directory = './voice_agent_service/clients/sonmez/data/'
    # Define sources with their category
    sources = {
        "product": os.path.join(data_directory, 'structured_tent_products.json'),
        "accessory": os.path.join(data_directory, 'scraped_accessories.json'),
        "faq": os.path.join(data_directory, 'FAQ.json')
    }

    all_documents = []
    ingestion_stats = {}

    for category, file_path in sources.items():
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}. Skipping.")
            continue

        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                # Create a summary text for embedding
                text_content = f"Name: {item.get('name', item.get('intent_name', ''))}. "
                if category == 'product':
                    text_content += f"Capacity: {item.get('capacity', {})}. "
                    text_content += f"Features: {item.get('benefits', [])}. "
                elif category == 'faq':
                    text_content += f"Question: {item.get('question_variants', [])}. Answer: {item.get('short_answer_text', '')}"
                
                # Create a stable document ID
                doc_id = f"{category}-{item.get('name', item.get('intent_name', '')).replace(' ', '-')}"

                # Add the category to the metadata
                metadata = item.copy()
                metadata['category'] = category
                metadata['doc_id'] = doc_id
                
                doc = Document(
                    page_content=text_content,
                    metadata=flatten_metadata(metadata)
                )
                all_documents.append(doc)
            
            ingestion_stats[category] = len(data)
            logging.info(f"Loaded {len(data)} documents from {os.path.basename(file_path)} under category '{category}'.")

    logging.info(f"Total documents prepared: {len(all_documents)}")
    logging.info(f"Ingestion stats: {ingestion_stats}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunked_documents = text_splitter.split_documents(all_documents)
    logging.info(f"Split documents into {len(chunked_documents)} chunks.")

    logging.info("Embedding documents and uploading to Pinecone...")
    pinecone_index_name = "sonmez-products"
    
    # Use from_documents to create or update the index
    PineconeVectorStore.from_documents(
        documents=chunked_documents,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        index_name=pinecone_index_name
    )

    logging.info(f"✅ Ingestion complete! Knowledge base '{pinecone_index_name}' is updated.")

if __name__ == "__main__":
    main()