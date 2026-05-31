import os
import json
import re
import threading
import logging
from datetime import datetime
from io import BytesIO

import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import PyPDF2
import google.generativeai as genai
import resend

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── API clients ───────────────────────────────────────────────────────────────
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
RESEND_KEY = os.getenv("RESEND_API_KEY", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

resend.api_key = RESEND_KEY

# ── State helpers ─────────────────────────────────────────────────────────────
DEFAULT_STATE = {
    "job_role": "",
    "cv_text": "",
    "cv_filename": "",
    "schedule_hour": 7,
    "last_run": None,
    "last_jobs": [],
}


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
                return {**DEFAULT_STATE, **data}
        except Exception:
            pass
    return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── HTML stripping ────────────────────────────────────────────────────────────
def strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"&[a-z]+;", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


# ── Job search helpers ────────────────────────────────────────────────────────
def search_remotive(role: str) -> list[dict]:
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": role, "limit": 20},
            timeout=10,
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
        results = []
        for j in jobs[:20]:
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "posted_date": j.get("publication_date", "")[:10] if j.get("publication_date") else "",
                "description": strip_html(j.get("description", ""))[:500],
                "url": j.get("url", "#"),
                "source": "Remotive",
            })
        return results
    except Exception as e:
        log.warning("Remotive error: %s", e)
        return []


def search_arbeitnow(role: str) -> list[dict]:
    try:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"q": role},
            timeout=10,
        )
        resp.raise_for_status()
        jobs = resp.json().get("data", [])
        results = []
        for j in jobs[:20]:
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "posted_date": datetime.fromtimestamp(j["created_at"]).strftime("%Y-%m-%d")
                if j.get("created_at") else "",
                "description": strip_html(j.get("description", ""))[:500],
                "url": j.get("url", "#"),
                "source": "Arbeitnow",
            })
        return results
    except Exception as e:
        log.warning("Arbeitnow error: %s", e)
        return []


def search_themuse(role: str) -> list[dict]:
    try:
        resp = requests.get(
            "https://www.themuse.com/api/public/jobs",
            params={"page": 1, "descending": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        all_jobs = resp.json().get("results", [])
        role_lower = role.lower()
        results = []
        for j in all_jobs:
            title = j.get("name", "")
            contents = strip_html(j.get("contents", ""))
            if role_lower in title.lower() or role_lower in contents.lower():
                locations = j.get("locations", [])
                location = locations[0]["name"] if locations else "Remote"
                companies = j.get("company", {})
                company = companies.get("name", "") if isinstance(companies, dict) else ""
                results.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "posted_date": j.get("publication_date", "")[:10] if j.get("publication_date") else "",
                    "description": contents[:500],
                    "url": j.get("refs", {}).get("landing_page", "#"),
                    "source": "The Muse",
                })
                if len(results) >= 10:
                    break
        return results
    except Exception as e:
        log.warning("The Muse error: %s", e)
        return []


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for j in jobs:
        key = (j["title"].lower().strip(), j["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out[:10]


def search_all_jobs(role: str) -> list[dict]:
    combined = search_remotive(role) + search_arbeitnow(role) + search_themuse(role)
    return deduplicate(combined)


# ── Gemini helpers ────────────────────────────────────────────────────────────
def rate_jobs_with_gemini(cv_text: str, jobs: list[dict]) -> list[dict]:
    if not GEMINI_KEY or not jobs:
        return jobs

    jobs_list = "\n".join(
        f"{i+1}. Title: {j['title']} | Company: {j['company']} | Description: {j['description'][:300]}"
        for i, j in enumerate(jobs)
    )
    prompt = (
        "You are a recruitment expert. Given the following CV and a list of job postings, "
        "score each job from 0 to 100 based on how well the CV matches the job requirements. "
        "Return a JSON array of objects with keys: index (1-based), score (integer 0-100), reason (one sentence max 20 words).\n\n"
        f"CV:\n{cv_text[:3000]}\n\nJobs:\n{jobs_list}\n\n"
        "Respond ONLY with the JSON array, no markdown, no explanation."
    )
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        ratings = json.loads(raw)
        for r in ratings:
            idx = r.get("index", 0) - 1
            if 0 <= idx < len(jobs):
                jobs[idx]["match_score"] = int(r.get("score", 0))
                jobs[idx]["match_reason"] = r.get("reason", "")
    except Exception as e:
        log.error("Gemini rating error: %s", e)
    return jobs


def tailor_cv_with_gemini(cv_text: str, job_title: str, company: str, description: str) -> str:
    if not GEMINI_KEY:
        return "Gemini API key not configured."
    prompt = (
        f"You are an expert CV writer. Rewrite the following CV to be ATS-friendly and tailored "
        f"for this specific job:\n\nJob Title: {job_title}\nCompany: {company}\n"
        f"Job Description:\n{description[:1500]}\n\n"
        f"Original CV:\n{cv_text[:4000]}\n\n"
        "Instructions:\n"
        "- Highlight skills and experience most relevant to this role\n"
        "- Use keywords from the job description naturally\n"
        "- Keep it under 2 pages (approx 700 words)\n"
        "- Use clean, ATS-readable formatting (no tables, no columns)\n"
        "- Return the complete tailored CV text only, no commentary."
    )
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        log.error("Gemini tailor error: %s", e)
        return f"Error generating tailored CV: {e}"


# ── Email helpers ─────────────────────────────────────────────────────────────
def send_email_digest(jobs: list[dict], role: str) -> bool:
    if not RESEND_KEY or not RECIPIENT_EMAIL:
        return False

    def score_badge(j):
        s = j.get("match_score")
        if s is None:
            return ""
        color = "#22c55e" if s >= 70 else "#f59e0b" if s >= 40 else "#ef4444"
        return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px;">{s}% Match</span>'

    cards = ""
    for j in jobs:
        cards += f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px;">
            <h3 style="margin:0 0 4px;color:#1f2937;">{j['title']}</h3>
            <p style="margin:0 0 8px;color:#6b7280;">{j['company']} &bull; {j['location']} &bull; {j['posted_date']}</p>
            {score_badge(j)}
            <p style="margin:8px 0;color:#374151;font-size:14px;">{j['description'][:300]}...</p>
            <a href="{j['url']}" style="background:#4F46E5;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:14px;">Apply Now →</a>
        </div>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;">
        <h1 style="color:#4F46E5;margin-bottom:4px;">Job Hunter AI</h1>
        <p style="color:#6b7280;">Your daily digest for <strong>{role}</strong> — {datetime.now().strftime('%B %d, %Y')}</p>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0;">
        {cards}
        <p style="color:#9ca3af;font-size:12px;margin-top:24px;">Sent by Job Hunter AI &bull; Unsubscribe</p>
    </body></html>"""

    try:
        resend.Emails.send({
            "from": "Job Hunter AI <onboarding@resend.dev>",
            "to": [RECIPIENT_EMAIL],
            "subject": f"Your Daily Job Digest: {role} — {len(jobs)} jobs found",
            "html": html,
        })
        return True
    except Exception as e:
        log.error("Resend error: %s", e)
        return False


# ── Scheduler ──────────────────────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="UTC")


def scheduled_digest():
    log.info("Running scheduled digest")
    state = load_state()
    role = state.get("job_role", "")
    if not role:
        log.info("No job role set, skipping digest")
        return
    jobs = search_all_jobs(role)
    if state.get("cv_text") and jobs:
        jobs = rate_jobs_with_gemini(state["cv_text"], jobs)
    state["last_jobs"] = jobs
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    send_email_digest(jobs, role)
    log.info("Scheduled digest complete, sent %d jobs", len(jobs))


def setup_scheduler(hour: int):
    scheduler.remove_all_jobs()
    scheduler.add_job(scheduled_digest, "cron", hour=hour, minute=0, id="daily_digest")
    log.info("Scheduler set for %02d:00 UTC", hour)


# ── API Routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    state = load_state()
    return jsonify({
        **state,
        "cv_text": "",  # never send CV text to frontend
        "gemini_configured": bool(GEMINI_KEY),
        "resend_configured": bool(RESEND_KEY),
        "recipient_configured": bool(RECIPIENT_EMAIL),
    })


@app.route("/api/save-role", methods=["POST"])
def api_save_role():
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip()
    if not role:
        return jsonify({"error": "Role is required"}), 400
    state = load_state()
    state["job_role"] = role
    save_state(state)
    return jsonify({"ok": True, "role": role})


@app.route("/api/upload-cv", methods=["POST"])
def api_upload_cv():
    if "cv" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["cv"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400
    try:
        pdf_bytes = f.read()
        reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        cv_text = "\n".join(text_parts).strip()
        if not cv_text:
            return jsonify({"error": "Could not extract text from PDF"}), 400
        state = load_state()
        state["cv_text"] = cv_text
        state["cv_filename"] = f.filename
        save_state(state)
        return jsonify({"ok": True, "filename": f.filename, "pages": len(reader.pages)})
    except Exception as e:
        log.error("CV upload error: %s", e)
        return jsonify({"error": f"Failed to process PDF: {e}"}), 500


@app.route("/api/save-schedule", methods=["POST"])
def api_save_schedule():
    data = request.get_json(silent=True) or {}
    try:
        hour = int(data.get("hour", 7))
        if not 0 <= hour <= 23:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Hour must be 0–23"}), 400
    state = load_state()
    state["schedule_hour"] = hour
    save_state(state)
    setup_scheduler(hour)
    return jsonify({"ok": True, "schedule_hour": hour})


@app.route("/api/search-jobs")
def api_search_jobs():
    state = load_state()
    role = state.get("job_role", "")
    if not role:
        return jsonify({"error": "No job role set. Please save a target role first."}), 400
    jobs = search_all_jobs(role)
    if not jobs:
        return jsonify({"error": "No jobs found. Try a broader role title."}), 404
    if state.get("cv_text"):
        jobs = rate_jobs_with_gemini(state["cv_text"], jobs)
    state["last_jobs"] = jobs
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    return jsonify({"ok": True, "jobs": jobs, "count": len(jobs)})


@app.route("/api/rate-jobs", methods=["POST"])
def api_rate_jobs():
    state = load_state()
    if not state.get("cv_text"):
        return jsonify({"error": "No CV uploaded. Please upload your CV first."}), 400
    jobs = state.get("last_jobs", [])
    if not jobs:
        return jsonify({"error": "No jobs to rate. Run a search first."}), 400
    if not GEMINI_KEY:
        return jsonify({"error": "Gemini API key not configured."}), 400
    jobs = rate_jobs_with_gemini(state["cv_text"], jobs)
    state["last_jobs"] = jobs
    save_state(state)
    return jsonify({"ok": True, "jobs": jobs})


@app.route("/api/send-digest", methods=["POST"])
def api_send_digest():
    state = load_state()
    jobs = state.get("last_jobs", [])
    role = state.get("job_role", "")
    if not jobs:
        return jsonify({"error": "No jobs to send. Run a search first."}), 400
    if not RESEND_KEY:
        return jsonify({"error": "Resend API key not configured."}), 400
    success = send_email_digest(jobs, role)
    if success:
        return jsonify({"ok": True, "message": f"Digest sent to {RECIPIENT_EMAIL}"})
    return jsonify({"error": "Failed to send email. Check Resend configuration."}), 500


@app.route("/api/trigger-digest", methods=["POST"])
def api_trigger_digest():
    state = load_state()
    if not state.get("job_role"):
        return jsonify({"error": "No job role set."}), 400

    def run():
        scheduled_digest()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Digest triggered in background"})


@app.route("/api/tailor-cv", methods=["POST"])
def api_tailor_cv():
    data = request.get_json(silent=True) or {}
    job_title = (data.get("job_title") or "").strip()
    company = (data.get("company") or "").strip()
    description = (data.get("description") or "").strip()
    if not job_title:
        return jsonify({"error": "job_title is required"}), 400
    state = load_state()
    if not state.get("cv_text"):
        return jsonify({"error": "No CV uploaded. Please upload your CV first."}), 400
    if not GEMINI_KEY:
        return jsonify({"error": "Gemini API key not configured."}), 400
    tailored = tailor_cv_with_gemini(state["cv_text"], job_title, company, description)
    return jsonify({"ok": True, "tailored_cv": tailored})


# ── Boot ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    state = load_state()
    setup_scheduler(state.get("schedule_hour", 7))
    scheduler.start()
    log.info("Job Hunter AI starting on port 5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
