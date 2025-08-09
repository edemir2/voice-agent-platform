# voice_agent_service/clients/sonmez/llm_logic/assistant_handler.py
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def format_docs_for_llm(docs):
    """
    I've rewritten this function to be much smarter. Instead of just
    mashing raw text together, it now intelligently extracts the most important,
    human-friendly details from each retrieved document's metadata. This ensures the
    LLM receives a clean, structured, and easy-to-understand context, which
    dramatically improves the quality of its answers.
    """
    if not docs:
        return "No relevant product information was found in the knowledge base."

    # I'm creating a set to keep track of product names to avoid showing duplicates.
    processed_products = set()
    formatted_context = []

    for doc in docs:
        # The metadata contains the original, complete JSON object for the product.
        product_data = doc.metadata
        product_name = product_data.get('name')

        if product_name and product_name not in processed_products:
            # Build a clean summary for each unique product.
            details = [
                f"--- Product: {product_name} ---",
                f"Capacity (Camping): {product_data.get('capacity', {}).get('camping', 'N/A')} people",
                f"Capacity (Glamping): {product_data.get('capacity', {}).get('glamping', 'N/A')} people",
                f"Weight: {product_data.get('weight', 'N/A')}",
                f"Inflation Time: {product_data.get('inflation_time', 'N/A')}",
                f"Price: Starts at ${product_data.get('colors', [{}])[0].get('price', 'N/A')}"
            ]
            formatted_context.append("\n".join(details))
            processed_products.add(product_name)

    return "\n\n".join(formatted_context)


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