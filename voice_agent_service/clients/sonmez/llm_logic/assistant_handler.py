import os
import json
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def format_docs_for_llm(docs):
    """
    Formats a list of documents for the LLM by creating a unique, readable context string.
    It de-duplicates documents based on 'doc_id' and formats each category differently.
    """
    if not docs:
        return "No relevant information was found."

    formatted_context = []
    # De-duplicate documents based on the 'doc_id' metadata field to avoid sending redundant info to the LLM.
    unique_docs = {doc.metadata.get('doc_id'): doc for doc in docs}.values()

    for doc in unique_docs:
        metadata = doc.metadata
        details = []
        category = metadata.get('category')

        if category == 'product':
            # Safely parse JSON string for capacity info
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
            
    return "\n\n".join(formatted_context)

def run_rag_assistant(user_input, history):
    """
    Runs the RAG assistant by retrieving relevant documents, formatting them,
    and passing them to the LLM with a structured prompt.
    """
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name="sonmez-products",
        embedding=OpenAIEmbeddings(model="text-embedding-3-small")
    )
    # Increased top_k to 20 for better recall on list-based and summary questions.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

    # The prompt is structured to guide the LLM in using the provided context effectively,
    # especially for questions that require counting, listing, or comparing items.
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
    
    # The RAG chain links the retriever, document formatter, prompt, LLM, and output parser.
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

    # Format the conversation history into a simple string for the prompt.
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # Invoke the chain with the user's input and the formatted history.
    answer = rag_chain.invoke({
        "question": user_input,
        "history": formatted_history
    })
    
    # Update the history with the latest turn of the conversation.
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": answer})
    
    return answer