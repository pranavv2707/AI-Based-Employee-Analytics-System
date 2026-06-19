import os
import json
import fitz
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from logger import logger
from rag.resume_prompts import EXTRACT_PROMPT, SCORE_PROMPT, COMPARE_PROMPT, SKILL_GAP_PROMPT

load_dotenv()

CHROMA_DIR = "rag/chroma_store/resumes"

#groq llm
def build_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
    )

def build_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"} #local hugging face
    )

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf") #use pymupdf and extract the text from the pdf first
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""

def parse_json_response(raw) -> dict:
    try:
        text = raw.content if hasattr(raw, "content") else str(raw)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1] #remove potential markdowns
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip()) #and also remove json prefixes also
    except Exception as e:
        logger.error(f"JSON parse failed: {e} | raw: {text[:200]}")
        return {}

def extract_metadata(resume_text: str) -> dict:
    try:
        llm = build_llm()
        prompt = EXTRACT_PROMPT.format(resume_text=resume_text[:3000])
        raw = llm.invoke(prompt) #get the prompt from resume_prompts.py file
        return parse_json_response(raw)
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {}

def ingest_resume(filename: str, pdf_bytes: bytes) -> dict:
    try:
        text = extract_text_from_pdf(pdf_bytes)
        if not text:
            return {"error": f"Could not extract text from {filename}"}

        metadata = extract_metadata(text)
        candidate_name = metadata.get("name", filename.replace(".pdf", ""))

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(text) #chunking strategy with parameters

        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "filename": filename,
                    "candidate_name": candidate_name,
                    "skills": ", ".join(metadata.get("skills", [])),
                    "experience_years": str(metadata.get("total_experience_years", 0)),
                    "chunk_index": i,
                }
            )
            for i, chunk in enumerate(chunks)
        ]

        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="resumes",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        vectorstore.add_documents(docs) #store the embeddings in chroma db as the vector database

        return {
            "message": f"{filename} ingested successfully.",
            "candidate_name": candidate_name,
            "skills": metadata.get("skills", []),
            "experience_years": metadata.get("total_experience_years", 0),
            "chunks": len(docs)
        }

    except Exception as e:
        logger.error(f"Ingest failed for {filename}: {e}")
        return {"error": str(e)}

def list_resumes() -> list:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="resumes",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        results = vectorstore.get()
        seen = set()
        candidates = []
        for meta in results.get("metadatas", []):
            name = meta.get("candidate_name", "Unknown")
            fname = meta.get("filename", "")
            if fname not in seen:
                seen.add(fname)
                candidates.append({
                    "filename": fname,
                    "candidate_name": name,
                    "skills": meta.get("skills", ""),
                    "experience_years": meta.get("experience_years", "0")
                })
        return candidates
    except Exception as e:
        logger.error(f"list_resumes failed: {e}")
        return []

def get_candidate_text(candidate_name: str) -> str:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="resumes",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        results = vectorstore.get(where={"candidate_name": candidate_name})
        chunks = results.get("documents", [])
        return " ".join(chunks)
    except Exception as e:
        logger.error(f"get_candidate_text failed: {e}")
        return ""

def screen_candidates(jd: str) -> list:
    try:
        candidates = list_resumes()
        if not candidates:
            return []

        llm = build_llm()
        scores = []

        for candidate in candidates:
            resume_text = get_candidate_text(candidate["candidate_name"])
            if not resume_text:
                continue

            prompt = SCORE_PROMPT.format(jd=jd, resume_text=resume_text[:3000])
            raw = llm.invoke(prompt)
            result = parse_json_response(raw)

            if result:
                scores.append(result)

        # sort by match_score descending
        scores.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return scores

    except Exception as e:
        logger.error(f"screen_candidates failed: {e}")
        return []

def compare_candidates(name_a: str, name_b: str, jd: str) -> dict:
    try:
        resume_a = get_candidate_text(name_a)
        resume_b = get_candidate_text(name_b)

        if not resume_a or not resume_b:
            return {"error": "Could not find one or both candidates."}

        llm = build_llm()
        prompt = COMPARE_PROMPT.format(
            jd=jd,
            name_a=name_a, resume_a=resume_a[:2000],
            name_b=name_b, resume_b=resume_b[:2000]
        )
        raw = llm.invoke(prompt)
        return parse_json_response(raw)

    except Exception as e:
        logger.error(f"compare_candidates failed: {e}")
        return {"error": str(e)}

def skill_gap_analysis(candidate_name: str, jd: str) -> dict:
    try:
        resume_text = get_candidate_text(candidate_name)
        if not resume_text:
            return {"error": f"Candidate {candidate_name} not found."}

        llm = build_llm()
        prompt = SKILL_GAP_PROMPT.format(jd=jd, resume_text=resume_text[:3000])
        raw = llm.invoke(prompt) #again take the prompt from the prompts file
        return parse_json_response(raw)

    except Exception as e:
        logger.error(f"skill_gap_analysis failed: {e}")
        return {"error": str(e)}

def clear_resumes() -> dict:
    try:
        embeddings = build_embeddings()
        vectorstore = Chroma(
            collection_name="resumes",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        vectorstore.delete_collection()
        return {"message": "All resumes cleared."}
    except Exception as e:
        logger.error(f"clear_resumes failed: {e}")
        return {"error": str(e)}