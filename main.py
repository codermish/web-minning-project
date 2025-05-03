import streamlit as st
import pandas as pd
import re
import docx
import tempfile
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --------------------------- Must be FIRST Streamlit command ---------------------------
st.set_page_config(page_title="Resume to Job Matcher", layout="wide")

# --------------------------- CSS & Background Image ---------------------------
st.markdown("""
<style>
/* Full-page image background */
body {
    background-image: url('https://img.freepik.com/free-vector/web-tech-white-background-with-binary-code-algorithm-numbers_1017-54579.jpg?t=st=1746311769~exp=1746315369~hmac=246656e0ad233ac3959d20358af843e446f88852cc596412ac35327edbc97192&w=1380');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}

/* Streamlit container */
.stApp {
    padding: 2rem;
    background-color: rgba(255, 255, 255, 0.92);
    border-radius: 16px;
    box-shadow: 0 0 30px rgba(0,0,0,0.1);
}

/* Font and layout */
html, body {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    margin: 0;
    padding: 0;
    border: 8px solid #861F41;
    border-radius: 20px;
}

/* Headings */
h1, h2, h3 {
    color: #861F41 !important;
    font-weight: 800 !important;
}

/* Misc elements */
.stMarkdown strong {
    color: #861F41 !important;
}

.stButton>button {
    background-color: #861F41;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 0.5em 1.2em;
}

.stDownloadButton>button {
    background-color: #861F41;
    color: white;
    font-weight: bold;
    border-radius: 8px;
}

.stFileUploader {
    border: 2px dashed #861F41;
    border-radius: 10px;
    padding: 10px;
}

.stDataFrame {
    border-radius: 10px;
    overflow: hidden;
    background: white;
}

.center-logo {
    display: flex;
    justify-content: center;
    margin-top: -20px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------- Title & Logo ---------------------------
st.markdown("""
<div class="center-logo">
    <img src="https://www.drupal.org/files/styles/grid-4-2x/public/Stevens-Official-PMSColor-R.png?itok=Ob2NjpoL" width="180"/>
</div>
<h1 style='text-align: center; color: #861F41;'>🎓 Stevens Resume-Based Job Recommender</h1>
""", unsafe_allow_html=True)

# --------------------------- Skill Pattern ---------------------------
SMART_SKILL_PATTERN = r"\b(Java|Python|AWS|React|Node\.js|Docker|Kubernetes|Golang|PostgreSQL|MongoDB|SQL|GraphQL|C#|Azure|Git|Redis|TypeScript|Flask|Django|TensorFlow|Pandas|FastAPI|Next\.js|Vue\.js|Angular|Jenkins|Scala|Spring Boot|C\+\+|MySQL|NoSQL|Elasticsearch|Firebase)\b"

# --------------------------- Resume Processing ---------------------------
def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

def extract_skills_from_text(text):
    found_skills = re.findall(SMART_SKILL_PATTERN, text, re.IGNORECASE)
    return sorted(set([skill.strip() for skill in found_skills]))

# --------------------------- Job Scraping ---------------------------
def scrape_remoteok_jobs():
    st.info("Scraping jobs from RemoteOK...")
    jobs = []
    try:
        url = "https://remoteok.com/remote-dev-jobs"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        job_rows = soup.find_all("tr", class_="job")
        for job in job_rows:
            try:
                title = job.find("h2", {"itemprop": "title"}).get_text(strip=True)
                company = job.find("h3", {"itemprop": "name"}).get_text(strip=True)
                location = job.find("div", class_="location")
                location = location.get_text(strip=True) if location else "Remote"
                link = "https://remoteok.com" + job.find("a", href=True)["href"]
                desc = job.get_text(separator=" ", strip=True)
                skills = extract_skills_from_text(desc)
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Skills": skills})
                if len(jobs) >= 70:
                    break
            except: continue
    except Exception as e:
        st.error(f"RemoteOK scrape failed: {e}")
    return jobs

def scrape_remotive_jobs():
    st.info("Scraping jobs from Remotive.io...")
    jobs = []
    try:
        url = "https://remotive.io/remote-jobs/software-dev"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("div", class_="job-list-card")
        for listing in listings:
            try:
                title = listing.find("h2").get_text(strip=True)
                company = listing.find("span", class_="company").get_text(strip=True)
                location = listing.find("div", class_="location")
                location = location.get_text(strip=True) if location else "Remote"
                link = "https://remotive.io" + listing.find("a", href=True)["href"]
                desc = listing.get_text(separator=" ", strip=True)
                skills = extract_skills_from_text(desc)
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Skills": skills})
                if len(jobs) >= 70:
                    break
            except: continue
    except Exception as e:
        st.error(f"Remotive scrape failed: {e}")
    return jobs

# --------------------------- Matching Logic ---------------------------
def rank_jobs_by_match(resume_skills, jobs):
    ranked = []
    for job in jobs:
        matched = set(resume_skills) & set(job['Skills'])
        score = round(len(matched) / len(resume_skills) * 100, 2) if resume_skills else 0
        if score > 0:
            job['Matched Skills'] = list(matched)
            job['Match Score (%)'] = score
            ranked.append(job)
    return sorted(ranked, key=lambda x: x['Match Score (%)'], reverse=True)

# --------------------------- Streamlit App Logic ---------------------------
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'resume_skills' not in st.session_state:
    st.session_state.resume_skills = []
if 'matched_df' not in st.session_state:
    st.session_state.matched_df = pd.DataFrame()

uploaded_file = st.file_uploader("📤 Upload your resume (DOCX or PDF)", type=["docx", "pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        if uploaded_file.name.endswith(".docx"):
            st.session_state.resume_text = extract_text_from_docx(tmp_file.name)
        else:
            with open(tmp_file.name, "rb") as pdf_file:
                st.session_state.resume_text = extract_text_from_pdf(pdf_file)
        st.session_state.resume_skills = extract_skills_from_text(st.session_state.resume_text)

st.markdown("## 🧠 Extracted Resume Skills")
st.write(st.session_state.resume_skills)

if st.button("🔍 Find Matching Jobs"):
    with st.spinner("🔎 Scraping and matching jobs..."):
        jobs = scrape_remoteok_jobs() + scrape_remotive_jobs()
        matched = rank_jobs_by_match(st.session_state.resume_skills, jobs)
        st.session_state.matched_df = pd.DataFrame(matched)

if not st.session_state.matched_df.empty:
    st.markdown("## ✅ Recommended Jobs (Ranked by Skill Match > 0%)")
    st.dataframe(st.session_state.matched_df[["Title", "Company", "Location", "Match Score (%)", "Matched Skills", "Link"]])
    csv = st.session_state.matched_df.to_csv(index=False)
    st.download_button("⬇️ Download Matches as CSV", data=csv, file_name="matched_jobs.csv", mime="text/csv")
