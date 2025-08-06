import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def format_retrieved_docs(docs):
    """
    Formats the output of the retriever into a single string.
    """
    return "\n\n".join(doc.page_content for doc in docs)

def run_rag_assistant(user_input, history):
    """
    Handles a user query using a corrected and robust RAG pipeline.
    """
    # 1. Set up the connection to your Pinecone vector store
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name="sonmez-products",
        embedding=OpenAIEmbeddings(model="text-embedding-3-small")
    )
    retriever = vectorstore.as_retriever()

    # 2. Define the prompt template
    template = """
    You are a friendly and conversational product expert for Sönmez Outdoor. Your role is to be precise and factual.
    1. If the user is just starting and says "hello" or nothing, greet them warmly and ask how you can help with our tent models.
    2. For all other questions, answer using ONLY the data provided in the 'Context' section.
    3. Report the data EXACTLY as it is written. Do NOT convert units (e.g., °F to °C) or change any values.
    4. If the information is not in the context, politely state that you do not have that specific information.

    Context:
    {context}

    Conversation History:
    {history}

    User Question: {question}

    Answer:
    """
    prompt = PromptTemplate.from_template(template)

    # 3. Set up the LLM
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

    # 4. Correctly construct the RAG chain
    rag_chain = (
        {
            "context": lambda x: format_retrieved_docs(retriever.invoke(x["question"])),
            "question": lambda x: x["question"],
            "history": lambda x: x["history"],
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # Format the history for the prompt
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # 5. Invoke the chain with a single dictionary containing all necessary keys
    answer = rag_chain.invoke({
        "question": user_input,
        "history": formatted_history
    })

    # Format the history for the prompt
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # 5. Invoke the chain with a single dictionary containing all necessary keys
    answer = rag_chain.invoke({
        "question": user_input,
        "history": formatted_history
    })
    
    # Update history for the next turn
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": answer})
    
    return answer