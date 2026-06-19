from flask import Flask, jsonify, request
from mysql.connector import IntegrityError, Error
from dotenv import load_dotenv
import logging
from db import get_conn, initialise_db
import re
from datetime import datetime
from rag.NLtoSQL import nl_to_sql
from rag.resume_rag import ingest_resume, list_resumes, screen_candidates, compare_candidates, skill_gap_analysis, clear_resumes
from rag.hr_rag import ingest_hr_doc, answer_hr_question, list_hr_docs, clear_hr_docs

load_dotenv()
logger = logging.getLogger(__name__)
app = Flask(__name__)

VALID_DEPARTMENTS = ["Engineering", "HR", "Finance", "Marketing", "Sales", "Operations", "Legal"]
VALID_JOB_TITLES  = ["Analyst", "Manager", "Engineer", "Director", "Specialist", "Coordinator", "Lead"]

def is_valid_email(email):
    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    if re.match(pattern, email):
        return True
    return False

@app.before_request
def startup():
    pass


@app.route("/getall", methods=["GET"])
def get_all():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.callproc("getallemployees")
        rows = []
        for result in c.stored_results():
            rows = result.fetchall()
        conn.close()
        employees = [
            {"id": r[0], "first_name": r[1], "last_name": r[2],"email": r[3], "department": r[4], "job_title": r[5],"salary": float(r[6]), "hire_date": str(r[7]), "created_at": str(r[8])
            }
            for r in rows
        ]
        return jsonify(employees)
    except Error as e:
        logger.error(f"GET /getall failed: {e}")
        return jsonify({"error": "Failed to fetch employees."}), 500


@app.route("/getemp/<int:emp_id>", methods=["GET"])
def get_one(emp_id):
    if emp_id <= 0:
        return jsonify({"error": "ID must be a positive integer."}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id = %s", (emp_id,))
        r = c.fetchone()
        conn.close()
        if not r:
            return jsonify({"error": f"Employee {emp_id} not found."}), 404
        return jsonify({
            "id": r[0], "first_name": r[1], "last_name": r[2],"email": r[3], "department": r[4], "job_title": r[5],"salary": float(r[6]), "hire_date": str(r[7]), "created_at": str(r[8])
        })
    except Error as e:
        logger.error(f"/getemp/<int:emp_id> failed: {e}")
        return jsonify({"error": "Failed to fetch employee."}), 500


@app.route("/create", methods=["POST"])
def create():
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    required = ["first_name", "last_name", "email", "department", "job_title", "salary", "hire_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if float(data.get("salary", 0)) <= 0:
        return jsonify({"error": "Salary must be greater than 0."}), 400
    if float(data.get("salary", 0)) > 10_000_000:
        return jsonify({"error": "Salary too high."}), 400
    if not is_valid_email(data["email"]):
        return jsonify({"error": f"Invalid email: {data['email']}"}), 400
    if data["department"] not in VALID_DEPARTMENTS:
        return jsonify({"error": "Invalid department."}), 400
    if data["job_title"] not in VALID_JOB_TITLES:
        return jsonify({"error": "Invalid job title."}), 400
    try:
        datetime.strptime(data["hire_date"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid hire_date. Use YYYY-MM-DD."}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO employees (first_name, last_name, email, department, job_title, salary, hire_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data["first_name"], data["last_name"], data["email"],
            data["department"], data["job_title"], data["salary"],
            data["hire_date"]
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({"message": "Employee created.", "id": new_id}), 201
    except IntegrityError as e:
        logger.error(f"POST /create integrity error: {e}")
        return jsonify({"error": "Email already exists."}), 409
    except Error as e:
        logger.error(f"POST /create failed: {e}")
        return jsonify({"error": "Failed to create employee."}), 500


@app.route("/update/<int:emp_id>", methods=["PUT"])
def update(emp_id):
    if emp_id <= 0:
        return jsonify({"error": "ID must be a positive integer."}), 400
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    allowed = ["first_name", "last_name", "email", "department", "job_title", "salary", "hire_date"]
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return jsonify({"error": "No valid fields provided to update."}), 400
    if "salary" in updates and float(updates["salary"]) <= 0:
        return jsonify({"error": "Salary must be greater than 0."}), 400
    if "email" in updates and not is_valid_email(updates["email"]):
        return jsonify({"error": f"Invalid email: {updates['email']}"}), 400
    if "department" in updates and updates["department"] not in VALID_DEPARTMENTS:
        return jsonify({"error": "Invalid department."}), 400
    if "job_title" in updates and updates["job_title"] not in VALID_JOB_TITLES:
        return jsonify({"error": "Invalid job title."}), 400
    if "hire_date" in updates:
        try:
            datetime.strptime(updates["hire_date"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid hire_date. Use YYYY-MM-DD."}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [emp_id]
        c.execute(f"UPDATE employees SET {set_clause} WHERE id = %s", values)
        conn.commit()
        if c.rowcount == 0:
            return jsonify({"error": f"Employee {emp_id} not found."}), 404
        conn.close()
        return jsonify({"message": f"Employee {emp_id} updated."})
    except IntegrityError as e:
        logger.error(f"PUT /update/{emp_id} integrity error: {e}")
        return jsonify({"error": "Email already exists."}), 409
    except Error as e:
        logger.error(f"PUT /update/{emp_id} failed: {e}")
        return jsonify({"error": "Failed to update employee."}), 500


@app.route("/delete/<int:emp_id>", methods=["DELETE"])
def delete(emp_id):
    if emp_id <= 0:
        return jsonify({"error": "ID must be a positive integer."}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
        conn.commit()
        if c.rowcount == 0:
            return jsonify({"error": f"Employee {emp_id} not found."}), 404
        conn.close()
        return jsonify({"message": f"Employee {emp_id} deleted."})
    except Error as e:
        logger.error(f"DELETE /delete/{emp_id} failed: {e}")
        return jsonify({"error": "Failed to delete employee."}), 500

#excel exporting
@app.route("/export/excel", methods=["GET"])
def export_excel():
    import pandas as pd
    import io
    from flask import send_file

    conn = get_conn()
    c = conn.cursor()
    c.callproc("getallemployees")

    rows = []
    cols = []
    for result in c.stored_results():      #stored procedure op
        cols = [d[0] for d in result.description]
        rows = result.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=cols)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Employees")
    buf.seek(0)

    return send_file(buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="employees.xlsx"
    )

@app.route("/rag/nl2sql", methods=["POST"])
def nl2sql():
    data = request.json
    question = data.get("query", "").strip()
    try:
        conn = get_conn()
        result = nl_to_sql(question, conn)
        conn.close()
        print("RESULT:", result)   # add this
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"POST /rag/nl2sql failed: {e}")
        return jsonify({"error": "NL2SQL request failed."}), 500


@app.route("/rag/resumes/upload", methods=["POST"])
def upload_resumes():
    if "files" not in request.files:
        return jsonify({"error": "No files provided."}), 400
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided."}), 400
    results = []
    for file in files:
        if not file.filename.endswith(".pdf"):
            results.append({"filename": file.filename, "error": "Only PDF files are supported."})
            continue
        pdf_bytes = file.read()
        result = ingest_resume(file.filename, pdf_bytes)
        results.append(result)
    return jsonify({"results": results})


@app.route("/rag/resumes/list", methods=["GET"])
def get_resumes():
    try:
        candidates = list_resumes()
        return jsonify({"candidates": candidates})
    except Exception as e:
        logger.error(f"GET /rag/resumes/list failed: {e}")
        return jsonify({"error": "Failed to list resumes."}), 500


@app.route("/rag/resumes/screen", methods=["POST"])
def screen():
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    jd = data.get("jd", "").strip()
    if not jd:
        return jsonify({"error": "Job description is required."}), 400
    try:
        results = screen_candidates(jd)
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        logger.error(f"POST /rag/resumes/screen failed: {e}")
        return jsonify({"error": "Screening failed."}), 500


@app.route("/rag/resumes/compare", methods=["POST"])
def compare():
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    name_a = data.get("candidate_a", "").strip()
    name_b = data.get("candidate_b", "").strip()
    jd     = data.get("jd", "").strip()
    if not name_a or not name_b:
        return jsonify({"error": "Both candidate names are required."}), 400
    if not jd:
        return jsonify({"error": "Job description is required."}), 400
    try:
        result = compare_candidates(name_a, name_b, jd)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"POST /rag/resumes/compare failed: {e}")
        return jsonify({"error": "Comparison failed."}), 500


@app.route("/rag/resumes/skillgap", methods=["POST"])
def skillgap():
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    candidate_name= data.get("candidate_name", "").strip()
    jd= data.get("jd", "").strip()
    if not candidate_name:
        return jsonify({"error": "Candidate name is required."}), 400
    if not jd:
        return jsonify({"error": "Job description is required."}), 400
    try:
        result = skill_gap_analysis(candidate_name, jd)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"POST /rag/resumes/skillgap failed: {e}")
        return jsonify({"error": "Skill gap analysis failed."}), 500


@app.route("/rag/resumes/clear", methods=["DELETE"])
def clear():
    try:
        result = clear_resumes()
        return jsonify(result)
    except Exception as e:
        logger.error(f"DELETE /rag/resumes/clear failed: {e}")
        return jsonify({"error": "Failed to clear resumes."}), 500


@app.route("/rag/hr/upload", methods=["POST"])
def upload_hr_docs():
    if "files" not in request.files:
        return jsonify({"error": "No files provided."}), 400
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided."}), 400
    results = []
    for file in files:
        if not file.filename.endswith(".pdf"):
            results.append({"filename": file.filename, "error": "Only PDF files are supported."})
            continue
        pdf_bytes = file.read()
        result = ingest_hr_doc(file.filename, pdf_bytes)
        results.append(result)
    return jsonify({"results": results})


@app.route("/rag/hr/question", methods=["POST"])
def hr_question():
    data = request.json
    if not data:
        return jsonify({"error": "Request body is required."}), 400
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required."}), 400
    if len(question) > 500:
        return jsonify({"error": "Question too long (max 500 characters)."}), 400
    try:
        result = answer_hr_question(question)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"POST /rag/hr/question failed: {e}")
        return jsonify({"error": "Failed to answer question."}), 500


@app.route("/rag/hr/list", methods=["GET"])
def list_hr():
    try:
        docs = list_hr_docs()
        return jsonify({"documents": docs})
    except Exception as e:
        logger.error(f"GET /rag/hr/list failed: {e}")
        return jsonify({"error": "Failed to list documents."}), 500


@app.route("/rag/hr/clear", methods=["DELETE"])
def clear_hr():
    try:
        result = clear_hr_docs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"DELETE /rag/hr/clear failed: {e}")
        return jsonify({"error": "Failed to clear documents."}), 500

if __name__ == "__main__":
    initialise_db()
    app.run(debug=True, port=5000)