# voice_agent_service/clients/sonmez/llm_logic/assistant_handler.py
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json

def format_docs_for_llm(docs):
    """
    Developer's Note: This is the final, robust version of the formatter. It correctly
    handles different document types (tents, accessories, FAQs) by checking for
    unique keys in their metadata. It avoids errors by only attempting to parse and
    format data that is relevant to the specific document type, ensuring a clean
    and accurate context is always generated for the LLM.
    """
    if not docs:
        return "No relevant product information was found in the knowledge base."

    processed_items = set()
    formatted_context = []

    for doc in docs:
        metadata = doc.metadata
        details = []

        # Determine a unique identifier for the document to avoid duplicates.
        unique_id = metadata.get('name') or metadata.get('intent_name')
        if not unique_id or unique_id in processed_items:
            continue

        # --- FIX: Universal logic to handle Tents, Accessories, and FAQs ---

        # Case 1: Document is a Tent Product (identified by 'capacity' and 'inflation_time')
        if 'capacity' in metadata and 'inflation_time' in metadata:
            capacity_info = json.loads(metadata.get('capacity', '{}'))
            colors_info = json.loads(metadata.get('colors', '[]'))
            
            details.append(f"--- Tent Product: {metadata.get('name')} ---")
            details.append(f"Capacity (Camping): {capacity_info.get('camping', 'N/A')} people")
            details.append(f"Capacity (Glamping): {capacity_info.get('glamping', 'N/A')} people")
            details.append(f"Weight: {metadata.get('weight', 'N/A')}")
            details.append(f"Inflation Time: {metadata.get('inflation_time', 'N/A')}")
            if colors_info:
                details.append(f"Price: Starts at ${colors_info[0].get('price', 'N/A')}")

        # Case 2: Document is an Accessory (identified by 'sku' and 'price')
        elif 'sku' in metadata and 'price' in metadata:
            details.append(f"--- Accessory: {metadata.get('name')} ---")
            details.append(f"Category: {metadata.get('category', 'N/A')}")
            details.append(f"Price: ${metadata.get('price')}")

        # Case 3: Document is an FAQ (identified by 'intent_name')
        elif 'intent_name' in metadata:
            question_variants = json.loads(metadata.get('question_variants', '[]'))
            details.append(f"--- FAQ: {metadata.get('intent_name')} ---")
            details.append(f"Relevant Questions: {', '.join(question_variants)}")
            details.append(f"Answer: {metadata.get('short_answer_voice')}")

        if details:
            formatted_context.append("\n".join(details))
            processed_items.add(unique_id)

    return "\n\n".join(formatted_context) if formatted_context else "No relevant information was found."

def run_rag_assistant(user_input, history):
    """
    Handles a user query using the final, corrected RAG pipeline.
    """
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name="sonmez-products",
        embedding=OpenAIEmbeddings(model="text-embedding-3-small")
    )
    # Developer's Note: I've updated the retriever to search for the top 5 most
    # relevant documents (k=5). This is crucial for answering summary questions
    # like "which tents fit 5 people," as it gives the AI more context to work with.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # Developer's Note: I've updated the prompt to be more robust. It now explicitly
    # tells the AI that it might receive context for multiple products and should use
    # all of it to formulate a comprehensive answer.
    template = """
    You are a helpful and friendly product expert for Sönmez Outdoor.
    Your task is to answer the user's question based *only* on the context provided.

    - If the context contains details for multiple products, use that information to answer comparative or summary questions.
    - If the user is just starting, greet them and ask how you can help.
    - Report data exactly as it is written. Do not make up information.
    - If the context does not contain the answer, politely say you don't have that information.

    Context:
    {context}

    Conversation History:
    {history}

    User Question: {question}

    Answer:
    """
    prompt = PromptTemplate.from_template(template)

    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_tokens=256
    )

    # Developer's Note: The chain is now simpler and more powerful. The key is that
    # retriever.invoke() now gets the top 5 docs, and our new format_docs_for_llm
    # function turns them into a perfect, clean context string for the prompt.
    rag_chain = (
        {
            "context": lambda x: format_docs_for_llm(retriever.invoke(x["question"])),
            "question": lambda x: x["question"],
            "history": lambda x: x["history"],
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    answer = rag_chain.invoke({
        "question": user_input,
        "history": formatted_history
    })
    
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": answer})
    
    return answer