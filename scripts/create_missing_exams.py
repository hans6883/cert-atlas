#!/usr/bin/env python3
"""
Create missing exams on QuizForge and queue question generation.
Reads exams_to_create.json, processes BATCH_SIZE at a time,
tracks progress in exams_created.json.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMS_FILE = REPO_ROOT / "exams_to_create.json"
PROGRESS_FILE = REPO_ROOT / "exams_created.json"
DB_PATH = Path.home() / "source" / "repos" / "web-scraper-mcp" / "data" / "blueprint_registry.db"
BASE_URL = "https://quizforge.ai"
BATCH_SIZE = 5
LOGIN_EMAIL = "stephen@glytic.com"
LOGIN_PASSWORD = "K@dena05@K@dena05@"

token = None
token_expiry = 0


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    safe = f"[{ts}] {msg}".encode("ascii", "replace").decode("ascii")
    print(safe, flush=True)


def curl_json(method, url, headers, body=None, timeout=60):
    cmd = ["curl", "-s", "-X", method, url]
    for h in headers:
        cmd.extend(["-H", h])
    if body:
        cmd.extend(["-H", "Content-Type: application/json", "-d", body])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def login():
    global token, token_expiry
    body = json.dumps({"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD})
    data = curl_json("POST", f"{BASE_URL}/api/auth/login",
                     ["Host: quizforge.ai"], body)
    if data and data.get("success"):
        token = data["token"]
        token_expiry = time.time() + 3500
        log("Login OK")
    else:
        log(f"Login FAILED: {data}")
        sys.exit(1)


def api(method, path, body=None):
    global token, token_expiry
    if time.time() > token_expiry - 300:
        login()
    headers = ["Host: quizforge.ai", f"Authorization: Bearer {token}"]
    return curl_json(method, f"{BASE_URL}{path}", headers, body)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"created": [], "failed": [], "batch_index": 0}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def run_batch():
    """Process one batch. Returns True if there's more work, False if done."""
    if not EXAMS_FILE.exists():
        log("No exams_to_create.json found")
        return False

    with open(EXAMS_FILE, encoding="utf-8") as f:
        all_exams = json.load(f)

    progress = load_progress()
    done_ids = {e["exam_id"] for e in progress["created"]} | {e["exam_id"] for e in progress["failed"]}
    remaining = [e for e in all_exams if e["exam_id"] not in done_ids]

    if not remaining:
        log(f"ALL DONE. Created: {len(progress['created'])}, Failed: {len(progress['failed'])}")
        return False

    batch = remaining[:BATCH_SIZE]
    log(f"Batch: {len(batch)} exams ({len(remaining)} remaining of {len(all_exams)} total)")

    # Load blueprint data for few-shot generation
    import sqlite3
    blueprints = {}
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        for row in conn.execute("SELECT exam_id, blueprint_json FROM exams"):
            blueprints[row[0]] = row[1]
        conn.close()
        log(f"Loaded {len(blueprints)} blueprints for few-shot enrichment")

    login()

    for exam in batch:
        title = exam["title"]
        bp_id = exam["exam_id"]

        # Create exam
        create_resp = api("POST", "/api/exams/create",
                         json.dumps({"title": title, "isPublic": True}))

        if not create_resp or not create_resp.get("success"):
            log(f"  FAIL create: {title} -> {create_resp}")
            progress["failed"].append({"exam_id": bp_id, "title": title, "error": str(create_resp)})
            save_progress(progress)
            continue

        qf_id = create_resp.get("testId")
        slug = create_resp.get("slug", "")
        log(f"  Created: {title} (ID={qf_id}, slug={slug})")

        # Build generation payload with blueprint data
        gen_payload = {
            "existingExamId": qf_id,
            "questionCount": 50,
            "difficulty": 3,
            "questionTypes": ["MCQ"],
            "includeExplanations": True,
            "generateFewShots": True,
        }

        # Inject blueprint as source content (domains + sample questions)
        if bp_id in blueprints:
            try:
                bp = json.loads(blueprints[bp_id])
                source_parts = []

                # Add domain/objective structure
                domains = bp.get("domains", [])
                if domains:
                    source_parts.append("EXAM DOMAINS:")
                    for d in domains:
                        weight = f" ({d['weight_percent']}%)" if d.get("weight_percent") else ""
                        source_parts.append(f"  {d.get('id','')} {d.get('name','')}{weight}")
                        for obj in d.get("objectives", [])[:3]:
                            source_parts.append(f"    - {obj.get('id','')} {obj.get('title','')}")

                # Add sample questions as few-shot examples
                samples = bp.get("sample_questions", [])
                if samples:
                    source_parts.append("\nSAMPLE QUESTIONS (match this style):")
                    for sq in samples[:3]:
                        source_parts.append(f"Q: {sq.get('question_text','')}")
                        for opt in sq.get("options", []):
                            source_parts.append(f"  {opt}")
                        source_parts.append(f"Answer: {sq.get('correct_answer','')}")
                        if sq.get("explanation"):
                            source_parts.append(f"Explanation: {sq['explanation'][:200]}")
                        source_parts.append("")

                if source_parts:
                    gen_payload["sourceContent"] = "\n".join(source_parts)[:2000]
                    log(f"  +blueprint: {len(domains)} domains, {len(samples)} samples")
            except (json.JSONDecodeError, KeyError):
                pass

        # Queue generation
        queue_resp = api("POST", "/api/admin/exam-builder/queue-generation",
                        json.dumps(gen_payload))

        if queue_resp and queue_resp.get("success"):
            log(f"  Queued: {title}")
            progress["created"].append({
                "exam_id": bp_id,
                "title": title,
                "qf_id": qf_id,
                "slug": slug,
                "job_id": queue_resp.get("jobId")
            })
        else:
            log(f"  FAIL queue: {title} -> {queue_resp}")
            progress["created"].append({
                "exam_id": bp_id,
                "title": title,
                "qf_id": qf_id,
                "slug": slug,
                "job_id": None,
                "queue_error": str(queue_resp)
            })

        save_progress(progress)
        time.sleep(1)  # gentle rate limiting

    progress["batch_index"] += 1
    save_progress(progress)

    remaining_after = len(all_exams) - len(progress["created"]) - len(progress["failed"])
    log(f"Batch done. Created: {len(progress['created'])}, Failed: {len(progress['failed'])}, Remaining: {remaining_after}")
    return remaining_after > 0


if __name__ == "__main__":
    run_batch()
