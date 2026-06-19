import streamlit as st
import requests
import pandas as pd
from datetime import date

API = "http://localhost:5000"

st.set_page_config(page_title="RAG enabled Employee Manager", layout="wide")
st.title("RAG enabled Employee Manager")


def api_call(method, path, **kwargs): #if extra responses are given kwargs is like <Object> obj
    try:
        resp = requests.request(method, f"{API}{path}", timeout=60, **kwargs) #wait only uptil 15 seconds max
        resp.raise_for_status()
        return resp, None
    except requests.exceptions.ConnectionError:
        return None, "Error:cannot connect to backend. please check if the backend is running on port 5000"
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("error", str(e)) if e.response else str(e)
        return None, f"Error: {detail}"
    except Exception as e:
        return None, f"Error: unexpected error: {e}"


def fetch_all():
    resp, err = api_call("GET", "/getall")
    if err:
        st.error(err)
        return pd.DataFrame()
    df = pd.DataFrame(resp.json())
    return df


tab_view, tab_add, tab_edit, tab_delete, tab_ai, tab_resume, tab_hr = st.tabs([
    "View & Export", "Add", " Edit", " Delete", " AI query" , "Resume analyser" , "HR Q&A"
])


with tab_view:
    st.subheader("All Employees")
    if st.button(" Refresh"):
        st.rerun()
#load everything is empty or else fetch the matching record from the db
    df = fetch_all()
    if not df.empty:
        search = st.text_input("Filter by any field", "")
        if search:
            mask = df.apply(lambda row: search.lower() in row.astype(str).str.lower().to_string(), axis=1) #on the run edition of the dataframe
            df = df[mask]

        st.markdown(f"**{len(df)} records**")
        st.dataframe(df, use_container_width=True, height=500)

        if st.button("Export as an excel file"):
            resp, err = api_call("GET", "/export/excel")
            if resp:
                st.download_button(
                    "Download excel sheet",
                    data=resp.content,
                    file_name="employees.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            elif err:
                st.error(err)

#addition of employee section
with tab_add:
    st.subheader("add a new employee")
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *")
            last_name  = st.text_input("Last Name *")
            email      = st.text_input("Email *")
            department = st.selectbox("Department *",
                ["Engineering", "HR", "Finance", "Marketing", "Sales", "Operations", "Legal"])
        with col2:
            job_title = st.selectbox("Job Title *",
                ["Analyst", "Manager", "Engineer", "Director", "Specialist", "Coordinator", "Lead"])
            salary    = st.number_input("Salary *", min_value=0.0, step=500.0, value=50000.0)
            hire_date = st.date_input("Hire Date *", value=date.today())
        submitted = st.form_submit_button("Add this Employee")

    if submitted:
        errors = []
        if not first_name.strip(): errors.append("a first name is required.")
        if not last_name.strip(): errors.append("last name is required.")
        if not email.strip():errors.append("An email address is required.")
        if  "." not in email or "@" not in email: errors.append("email address is required.")
        if salary <= 0: errors.append("the salary must be not be invalid.")
        if len(first_name.strip()) > 50: errors.append("First name is too long (max 50 characters).")
        if len(last_name.strip()) > 50: errors.append("Last name is too long (max 50 characters).")
        if errors:
            for e in errors: st.error(e)
        else:
            resp, err = api_call("POST", "/create", json={
                "first_name": first_name.strip(), "last_name": last_name.strip(),
                "email": email.strip(), "department": department,
                "job_title": job_title, "salary": salary,
                "hire_date": str(hire_date)
            })
            if resp: st.success(f"Employee added successfully. ID: {resp.json().get('id')}")
            elif err: st.error(err)

with tab_edit:
    st.subheader("Edit Employee")
    emp_id = st.number_input("Employee ID", min_value=1, key="edit_id")
    if st.button("Load"):
        st.session_state.pop("edit_data", None)   # clear previous record first
        resp, err = api_call("GET", f"/getemp/{emp_id}")
        if resp:
            st.session_state["edit_data"] = resp.json()
        elif err:
            st.error(f"No record found for ID {int(emp_id)}. Please enter a valid Employee ID.")
            st.session_state.pop("edit_data", None)

    if "edit_data" in st.session_state:
        emp = st.session_state["edit_data"]
        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                u_first  = st.text_input("First Name", value=emp.get("first_name", ""))
                u_last   = st.text_input("Last Name",  value=emp.get("last_name", ""))
                u_email  = st.text_input("Email",      value=emp.get("email", ""))
                u_dept   = st.text_input("Department", value=emp.get("department", ""))
            with col2:
                u_title  = st.text_input("Job Title",  value=emp.get("job_title", ""))
                u_salary = st.number_input("Salary", value=float(emp.get("salary", 0)), min_value=0.0)
                u_hire   = st.date_input("Hire Date", value=date.fromisoformat(emp["hire_date"][:10]))
            save = st.form_submit_button("Save and update")

        if save:
            errors = []
            if not u_first.strip(): errors.append("a first name is required.")
            if not u_last.strip(): errors.append("last name is required.")
            if not u_email.strip(): errors.append("An email address is required.")
            if "." not in u_email or "@" not in u_email: errors.append("email address is required.")
            if u_salary <= 0: errors.append("the salary must be not be invalid.")
            if len(u_first.strip()) > 50: errors.append("First name is too long (max 50 characters).")
            if len(u_last.strip()) > 50: errors.append("Last name is too long (max 50 characters).")
            if errors:
                for e in errors: st.error(e)
            else:
                resp, err = api_call("PUT", f"/update/{emp_id}", json={
                "first_name": u_first.strip(), "last_name": u_last.strip(),
                "email": u_email.strip(), "department": u_dept.strip(),
                "job_title": u_title.strip(), "salary": u_salary,
                "hire_date": str(u_hire)
            })
                if resp:
                    st.success(f"Employee {int(emp_id)} has been updated successfully.")
                    fresh, _ = api_call("GET", f"/getemp/{emp_id}")  # fetch updated record from db
                    if fresh:
                        st.session_state["edit_data"] = fresh.json()
                    else:
                        st.session_state.pop("edit_data", None)
                    st.rerun()
                elif err:
                    st.error(err)

with tab_delete:
    st.subheader("Delete Employee")
    del_id = st.number_input("Employee ID", min_value=1, key="del_id")
    if st.button("Preview"):
        st.session_state.pop("delpreview", None)  # clear previous record first
        resp, err = api_call("GET", f"/getemp/{del_id}")
        if resp: st.session_state["delpreview"] = resp.json()
        elif err:
            st.error(f"No record found for ID {int(del_id)}. Please enter a valid Employee ID.")
            st.session_state.pop("delpreview", None)

    if "delpreview" in st.session_state:
        emp = st.session_state["delpreview"]
        st.warning(f"Delete: **{emp['first_name']} {emp['last_name']}** ({emp['email']})")
        if st.button(" Confirm Delete", type="primary"):
            resp, err = api_call("DELETE", f"/delete/{del_id}")
            if resp:
                st.success(" Deleted.")
                st.session_state.pop("delpreview", None)
            elif err:
                st.error(err)

with tab_ai:
    st.subheader("Ask questions to your database!")
    st.markdown("Results from your database can be gotten by simple english commands")

    ex = [
        "show me all engineering employees with salary above 50000",
        "who are the top 5 highest paid employees?",
        "list all emails of the employees in the HR department",
        "how many employees were hired after 2022 in the legal team?",
    ]
    st.markdown("**Example queries:**")
    for e in ex:
        st.markdown(f"- *{e}*")

    st.divider()

    query = st.text_area("Your question", placeholder="e.g. Show me all finance dept employees who joined after 2019", height=80)

    if st.button("Run Query", type="primary"):
        if not query.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Working on your query..."):
                resp, err = api_call("POST", "/rag/nl2sql", json={"query": query})

            if err:
                st.error(err)
            else:
                data = resp.json()
                if "error" in data:
                    st.error(f"An error occurred:{data['error']}")
                    if data.get("sql"):
                        st.code(data["sql"], language="sql")
                else:
                    st.success(f"{data['count']} result(s) found")

                    with st.expander("View Generated SQL"):
                        st.code(data["sql"], language="sql")

                    if data["results"]:
                        df = pd.DataFrame(data["results"])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Query ran successfully and returned no rows.")

with tab_resume:
    st.header("Resume Screener")
    st.subheader("Drop in resumes for a job description and rank resumes based on their suitability")
    st.markdown("Upload resumes, paste a job description, and get AI-powered candidate ranking.")
    st.markdown("#### Upload Resumes")
    uploaded_files = st.file_uploader("Upload PDF resumes", type=["pdf"], accept_multiple_files=True)

    if st.button("Upload and Process"):
        if not uploaded_files:
            st.error("Please upload at least one PDF.")
        else:
            files = [("files", (f.name, f.read(), "application/pdf")) for f in uploaded_files]
            with st.spinner("Extracting and embedding resumes..."):
                resp, err = api_call("POST", "/rag/resumes/upload", files=files)
            if err:
                st.error(err)
            else:
                for r in resp.json().get("results", []):
                    if "error" in r:
                        st.error(f"{r.get('filename')}: {r['error']}")
                    else:
                        st.success(f"{r.get('candidate_name')} — {r.get('chunks')} chunks | skills: {', '.join(r.get('skills', []))}")

    st.divider()

    st.markdown("#### The list of uploaded candidates:")
    if st.button("refresh list"):
        resp, err = api_call("GET", "/rag/resumes/list")
        if resp:
            candidates = resp.json().get("candidates", [])
            if candidates:
                df = pd.DataFrame(candidates)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No resumes uploaded yet.")
        elif err:
            st.error(err)

    st.divider()

    st.markdown("#### Job Description")
    jd = st.text_area("Enter the detailed job description you would like to compare the resumes with:",placeholder = "Job description")
    st.divider()

    st.markdown("#### screen & rank candidates")
    if st.button("screen candidates", type="primary"):
        if not jd.strip():
            st.error("Please paste a job description first.")
        else:
            with st.spinner("reviewing and ranking the candidates"):
                resp, err = api_call("POST", "/rag/resumes/screen", json={"jd": jd}) #call the model here and get the response
            if err: # the response will contain a score and a recommendability and also a list of the matched and misisng skills and with a summary
                st.error(err)
            else:
                results = resp.json().get("results", [])
                if not results:
                    st.info("No candidates found. Upload some resumes first.")
                else:
                    st.success(f"{len(results)} candidate(s) ranked")
                    for i, r in enumerate(results):
                        score = r.get("match_score", 0)
                        color = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
                        with st.expander(f"{color} #{i+1} {r.get('name')}      |  {score}% match | {r.get('recommendation')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Matched Skills**")
                                for s in r.get("matched_skills", []):
                                    st.markdown(f"- {s}") #bullet point the matched skills
                            with col2:
                                st.markdown("**Missing Skills**")
                                for s in r.get("missing_skills", []):
                                    st.markdown(f"- {s}") #and also the missing skills too
                            st.markdown(f"**Summary:** {r.get('summary')}")

    st.divider()

    st.markdown("#### Compare Two Candidates")
    col1, col2 = st.columns(2)
    with col1:
        canda = st.text_input("Candidate A name")
    with col2:
        candb = st.text_input("Candidate B name")

    if st.button("Compare"):
        if not canda.strip() or not candb.strip():
            st.error("Please enter both candidate names.")
        elif not jd.strip():
            st.error("Please paste a job description above first.")
        else:
            with st.spinner("Comparing candidates..."):
                resp, err = api_call("POST", "/rag/resumes/compare", json={
                    "candidate_a": canda.strip(),
                    "candidate_b": candb.strip(),
                    "jd": jd
                })
            if err:
                st.error(err)
            else:
                result = resp.json()
                st.success(f"better choice: **{result.get('winner')}**")
                st.markdown(f"**reason:** {result.get('reason')}")
                col1, col2 = st.columns(2)
                for col, key, name in [(col1, "candidate_a", canda), (col2, "candidate_b", candb)]:
                    with col:
                        data = result.get(key, {})
                        st.markdown(f"**{name}** — Score: {data.get('score')}%")
                        st.markdown("Strengths:")
                        for s in data.get("strengths", []): st.markdown(f"- {s}")
                        st.markdown("Weaknesses:")
                        for s in data.get("weaknesses", []): st.markdown(f"- {s}")

    st.divider()

    st.markdown("#### skill gap analysis")
    g_can = st.text_input("please enter the candidate name for skill gap analysis")

    if st.button("analyse skill gap"):
        if not g_can.strip():
            st.error("please enter a candidate name.")
        elif not jd.strip():
            st.error("please enter a job description.")
        else:
            with st.spinner("analysing skill gap..."):
                resp, err = api_call("POST", "/rag/resumes/skillgap", json={
                    "candidate_name": g_can.strip(),
                    "jd": jd
                })
            if err:
                st.error(err)
            else:
                result = resp.json()
                st.markdown(f"**Readiness:** {result.get('readiness')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"** skills which {g_can} already has :**")
                    for s in result.get("has_skills", []): st.markdown(f"- {s}")
                    st.markdown(f"** critical skills which {g_can} is misisng: :**")
                    for s in result.get("missing_critical", []): st.markdown(f"- {s}")
                with col2:
                    st.markdown(f"** preferable skills which {g_can} is missing :**")
                    for s in result.get("missing_nice_to_have", []): st.markdown(f"- {s}")
                    st.markdown(f"**upskilling suggestions for {g_can}**")
                    for s in result.get("upskilling_suggestions", []): st.markdown(f"- {s}")

    st.divider()

    if st.button("Clear All Resumes", type="primary"):
        resp, err = api_call("DELETE", "/rag/resumes/clear")
        if resp: st.success("All resumes cleared.")
        elif err: st.error(err)

with tab_hr:
    st.header("HR Q&A")
    st.subheader("Drop in HR documents and ask questions from them")
    st.markdown("#### Upload documents")
    uploaded_files = st.file_uploader("Upload document(s)", type=["pdf"], accept_multiple_files=True)

    if st.button("Upload and Process", key="hr_upload_and_process"):
        if not uploaded_files:
            st.error("Please upload at least one PDF.")
        else:
            files = [("files", (f.name, f.getvalue(), "application/pdf")) for f in uploaded_files]  # fixed: getvalue()
            with st.spinner("Extracting and embedding the document(s)..."):
                resp, err = api_call("POST", "/rag/hr/upload", files=files)  # fixed: files= not json=
            if err:
                st.error(err)
            else:
                for r in resp.json().get("results", []):
                    if "error" in r:
                        st.error(f"{r.get('filename')}: {r['error']}")
                    else:
                        st.success(f"{r.get('filename')} has been successfully uploaded")

    st.divider()

    st.markdown("#### Enter the question here:")
    question = st.text_area("Enter what you would like to know from your uploaded document here:",
                            placeholder="What are the updated leave policies after 2024?")
    st.divider()

    if st.button("Obtain answers"):
        if not question.strip():
            st.error("Please enter a question first.")
        else:
            with st.spinner(f"Obtaining answer..."):
                resp, err = api_call("POST", "/rag/hr/question", json={"question": question})  # fixed: err not arr
            if err:
                st.error(err)
            else:
                data = resp.json()
                st.markdown(f"**Answer:** {data.get('answer', 'No answer returned.')}")
                if data.get("sources"):
                    st.caption(f"Sources: {', '.join(data.get('sources', []))}")
