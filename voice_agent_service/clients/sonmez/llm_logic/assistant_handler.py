import os
import json
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def format_docs_for_llm(docs):
    if not docs:
        return "No relevant information was found."

    formatted_context = []
    processed_ids = set()

    for doc in docs:
        metadata = doc.metadata
        doc_id = metadata.get('doc_id')

        if not doc_id or doc_id in processed_ids:
            continue
        
        details = []
        category = metadata.get('category')

        if category == 'product':
            capacity_info = json.loads(metadata.get('capacity', '{}'))
            details.append(f"--- Tent Product: {metadata.get('name')} ---")
            details.append(f"Capacity (Camping): {capacity_info.get('camping', 'N/A')} people")
            details.append(f"Capacity (Glamping): {capacity_info.get('glamping', 'N/A')} people")
            details.append(f"Weight: {metadata.get('weight', 'N/A')}")
        
        elif category == 'accessory':
            details.append(f"--- Accessory: {metadata.get('name')} ---")
            details.append(f"Price: ${metadata.get('price')}")

        elif category == 'faq':
            details.append(f"--- FAQ on '{metadata.get('intent_name')}' ---")
            details.append(f"Answer: {metadata.get('short_answer_voice')}")

        if details:
            formatted_context.append("\n".join(details))
            processed_ids.add(doc_id)
            
    return "\n\n".join(formatted_context)

def run_rag_assistant(user_input, history):
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name="sonmez-products",
        embedding=OpenAIEmbeddings(model="text-embedding-3-small")
    )
    # Increase top_k to 15 for better recall on list-based questions
    retriever = vectorstore.as_retriever(search_kwargs={"k": 15})

    # Developer's Note: I've updated the prompt to be more robust. It now explicitly
    # tells the AI that it might receive context for multiple products and should use
    # all of it to formulate a comprehensive answer.
    template = """
    You are a helpful and friendly product expert for Sönmez Outdoor.
    Your task is to answer the user's question based *only* on the context provided.

    - If the context contains details for multiple products, use that information to answer comparative or summary questions. For questions like "how many" or "list all", count or list all the items provided in the context.
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