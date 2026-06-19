import os
import re
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from logger import logger
from langchain_groq import ChatGroq
load_dotenv()

SCHEMA = """
Table: employees
Columns:
  - id          INT            (auto-increment primary key)
  - first_name  VARCHAR(50)
  - last_name   VARCHAR(50)
  - email       VARCHAR(100)
  - department  VARCHAR(50)    (values: Engineering, HR, Finance, Marketing, Sales, Operations, Legal)
  - job_title   VARCHAR(50)    (values: Analyst, Manager, Engineer, Director, Specialist, Coordinator, Lead)
  - salary      DECIMAL(10,2)
  - hire_date   DATE
  - created_at  TIMESTAMP
"""
#manually injecting the schema to langchain to ensure only selected data is given to the agent
PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template="""You are a MySQL expert. Given the schema below, write a single valid MySQL SELECT query for the user's question.
Return ONLY the raw SQL query. No explanations or markdowns or backticks. No semicolons at the end, just the SQL Query.

Schema:
{schema}

Question: {question}

SQL:"""
)

BLOCKED_KEYWORDS = ["drop", "delete", "insert", "update", "truncate", "alter", "create", "replace", "grant", "revoke"]
#guardrails so that any modification of the database inst done

def build_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
    )


def validate_sql(sql: str) -> tuple[bool, str]:
    cleaned = sql.strip().lower()

    if not cleaned.startswith("select"):
        return False, "Only SELECT queries are allowed."

    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", cleaned):
            return False, f"Blocked keyword detected: '{kw}'"

    return True, ""

#first remove any accidental markdown answers or any unwanted punctuation that my have slipped
def cleaned_sql(raw: str) -> str:
    sql = raw.strip()
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.rstrip(";").strip()
    return sql


def nl_to_sql(question: str, conn) -> dict:
    try:
        llm = build_llm()
        chain = PROMPT | llm

        raw = chain.invoke({"schema": SCHEMA, "question": question})
        sql = cleaned_sql(raw.content if hasattr(raw, "content") else str(raw))

        valid, reason = validate_sql(sql)
        if not valid:
            logger.error(f"The given request may contain a blocked query: {sql} ; reason: {reason}")
            return {"error": reason, "sql": sql}

        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()

        results = [dict(zip(columns, row)) for row in rows]
        return {"sql": sql, "results": results, "count": len(results)}

    except Exception as e:
        logger.error(f"NLtoSQL has failed: {e}")
        return {"error": str(e), "sql": ""}