import os
import fitz
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from logger import logger

load_dotenv()

CHROMA_DIR = "rag/chroma_store/hr_docs"

HR_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert HR policy assistant. Answer the question below using ONLY the document excerpts provided.
If the answer is not found in the documents, say "I could not find this information in the uploaded documents."
Be specific, cite relevant policy details, and keep the answer concise.

Document excerpts:
{context}

Question: {question}

Answer:"""
)


def build_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
    )


def build_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"}
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def ingest_hr_doc(filename: str, pdf_bytes: bytes) -> dict:
    try:
        text = extract_text_from_pdf(pdf_bytes)
        if not text:
            return {"error": f"Could not extract text from {filename}"}

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_text(text)

        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "filename": filename,
                    "chunk_index": i,
                }
            )
            for i, chunk in enumerate(chunks)
        ]

        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="hr_docs",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        vectorstore.add_documents(docs)

        return {
            "filename": filename,
            "message": f"{filename} ingested successfully.",
            "chunks": len(docs)
        }

    except Exception as e:
        logger.error(f"HR doc ingest failed for {filename}: {e}")
        return {"error": str(e)}


def answer_hr_question(question: str) -> dict:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="hr_docs",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )

        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(question)

        if not relevant_docs:
            return {"answer": "No documents found. Please upload HR documents first."}

        context = "\n\n".join([
            f"[From: {doc.metadata.get('filename', 'unknown')}]\n{doc.page_content}"
            for doc in relevant_docs
        ])

        sources = list(set([doc.metadata.get("filename", "unknown") for doc in relevant_docs]))

        llm = build_llm()
        chain = HR_PROMPT | llm
        raw = chain.invoke({"context": context, "question": question})
        answer = raw.content if hasattr(raw, "content") else str(raw)

        return {
            "answer": answer.strip(),
            "sources": sources,
            "chunks_used": len(relevant_docs)
        }

    except Exception as e:
        logger.error(f"answer_hr_question failed: {e}")
        return {"error": str(e)}


def list_hr_docs() -> list:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="hr_docs",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        results = vectorstore.get()
        seen = set()
        docs = []
        for meta in results.get("metadatas", []):
            fname = meta.get("filename", "")
            if fname not in seen:
                seen.add(fname)
                docs.append({"filename": fname})
        return docs
    except Exception as e:
        logger.error(f"list_hr_docs failed: {e}")
        return []


def clear_hr_docs() -> dict:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="hr_docs",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        vectorstore.delete_collection()
        return {"message": "All HR documents cleared."}
    except Exception as e:
        logger.error(f"clear_hr_docs failed: {e}")
        return {"error": str(e)}