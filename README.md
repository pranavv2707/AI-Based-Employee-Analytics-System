# AI-Based Natural Language Employee Analytics System

A full-stack HR analytics platform that lets you query employee data in plain English, screen resumes with AI, and analyse HR documents — all powered by LLMs and a RAG pipeline.

---

## Tech Stack

**Backend:** Flask, MySQL, LangChain, ChromaDB, PyMuPDF  
**AI:** Groq (NL2SQL + embeddings , resume screening + document analysis)  
**Frontend:** Streamlit

---

## Features

### Phase 1 — NL to SQL Query Engine
Ask questions about employee data in plain English. Groq generates a validated SQL SELECT query using the injected schema, executes it against MySQL, and returns results as a data grid.

### Phase 2 — Resume Screener
Upload multiple candidate PDFs. Each resume is parsed with PyMuPDF, chunked, embedded with Groq embeddings, and stored in ChromaDB. A screening question retrieves the most relevant chunks and passes them to Groq, which returns a ranked answer with candidate names and reasoning.

### Phase 3 — HR Document Analyser
Upload HR policy documents, handbooks, or compliance PDFs. Same RAG pipeline as Phase 2 — PyMuPDF parsing, chunking, Groq embeddings, ChromaDB storage. Ask any question and Groq returns a synthesized answer grounded in the actual document content.

---

## Project Structure

```
├── api.py            # Flask API routes for all three phases
├── db.py             # MySQL connection and query execution
├── frontend.py       # Streamlit UI
├── errorlogs.py      # Error logging utilities
├── rag/              # RAG pipeline — chunking, embedding, ChromaDB
├── requirements.txt
└── .gitignore
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/pranavv2707/AI-Based-Natural-Language-Employee-Analytics-System.git
cd AI-Based-Natural-Language-Employee-Analytics-System
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```
**3. Set environment variables**

Create a `.env` file in the root:
```
GROQ_API_KEY=your_groq_api_key
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DB=your_database
```

**4. Run the backend**
```bash
python api.py
```

**5. Run the frontend**
```bash
streamlit run frontend.py
```
---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for NL2SQL and embeddings |
| `MYSQL_HOST` | MySQL host |
| `MYSQL_USER` | MySQL username |
| `MYSQL_PASSWORD` | MySQL password |
| `MYSQL_DB` | Database name |

