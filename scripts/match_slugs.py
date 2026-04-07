#!/usr/bin/env python3
"""
Match blueprint registry exam IDs to real QuizForge slugs.
Uses exact matching, code extraction, alias lookup, and title overlap.
Validates matches to avoid cross-vendor mismatches.
"""

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path.home() / "source" / "repos" / "web-scraper-mcp" / "data" / "blueprint_registry.db"
QF_PATH = REPO_ROOT / "qf_exams.json"
OUT_PATH = REPO_ROOT / "slug_map.json"


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def extract_codes(s):
    """Extract exam-code-like patterns from a string.

    Returns codes as they appear (preserving letter-number boundaries)
    so AZ-900 becomes 'az-900' not 'az900', preventing false matches.
    """
    n = norm(s)
    codes = set()
    # letter-dash-number patterns: az-900, sy0-701, mb-910, dp-700
    for m in re.finditer(r"([a-z]{1,5})-(\d{2,4}[a-z]?)", n):
        codes.add(m.group(0))  # keep hyphen: az-900
    # letter-number with no dash: az900 in slugs
    for m in re.finditer(r"(?<![a-z])([a-z]{1,5})(\d{2,4}[a-z]?)(?![a-z0-9])", n):
        codes.add(m.group(1) + "-" + m.group(2))  # normalize to az-900
    # letter-number-letter-number: clf-c02, saa-c03
    for m in re.finditer(r"([a-z]{2,5})-([a-z]\d{2})", n):
        codes.add(m.group(0))
    # number-number: 200-301
    for m in re.finditer(r"(\d{3})-(\d{3})", n):
        codes.add(m.group(0))
    for m in re.finditer(r"(?<!\d)(\d{3})(\d{3})(?!\d)", n):
        codes.add(m.group(1) + "-" + m.group(2))
    # Pure alpha codes (3-8 chars uppercase): CISSP, CCNA, OSCP
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", s).strip()
    for word in raw.split():
        if re.match(r"^[A-Z]{3,8}$", word):
            codes.add(word.lower())
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", word).lower()
        if 3 <= len(cleaned) <= 10 and cleaned not in {
            "the", "and", "for", "exam", "certified", "professional",
            "associate", "specialist", "foundation", "practitioner",
            "advanced", "administrator", "developer", "engineer",
            "analyst", "consultant", "manager", "architect",
        }:
            codes.add(cleaned)
    return codes


def main():
    # Load QF exams
    with open(QF_PATH, encoding="utf-8") as f:
        qf_exams = json.load(f)

    # Build QF indexes
    qf_by_slug = {e["slug"]: e for e in qf_exams}
    qf_by_norm_slug = {norm(e["slug"]): e["slug"] for e in qf_exams}
    qf_by_norm_title = {norm(e["title"]): e["slug"] for e in qf_exams}

    # Code -> slug list
    qf_code_to_slugs = {}
    for e in qf_exams:
        slug = e["slug"]
        for code in extract_codes(slug) | extract_codes(e.get("title", "")):
            qf_code_to_slugs.setdefault(code, set()).add(slug)

    # Blueprint data
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        """SELECT exam_id,
                  json_extract(blueprint_json, '$.exam_name'),
                  json_extract(blueprint_json, '$.exam_code'),
                  json_extract(blueprint_json, '$.certifying_body')
           FROM exams"""
    ).fetchall()
    aliases_raw = conn.execute("SELECT alias, exam_id FROM aliases").fetchall()
    conn.close()

    alias_map = {}
    for a, eid in aliases_raw:
        alias_map.setdefault(eid, []).append(a)

    matched = {}
    unmatched_list = []

    for exam_id, exam_name, exam_code, body in rows:
        ename = exam_name or ""
        ecode = exam_code or ""
        ebody = body or ""
        n_name = norm(ename)
        n_id = norm(exam_id)

        found = None

        # 1. Exact normalized matches
        if n_id in qf_by_norm_slug:
            found = qf_by_norm_slug[n_id]
        elif n_name in qf_by_norm_title:
            found = qf_by_norm_title[n_name]
        elif n_name in qf_by_norm_slug:
            found = qf_by_norm_slug[n_name]

        # 2. Substring match: blueprint ID is contained in or contains a QF slug
        #    e.g. "cisco-ccna-200-301" matches "cisco-ccna-200-301-a58740b1"
        if not found and len(n_id) >= 8:
            substr_matches = [
                slug for ns, slug in qf_by_norm_slug.items()
                if ns.startswith(n_id) or n_id.startswith(ns)
                or n_id in ns or ns in n_id
            ]
            if len(substr_matches) == 1:
                found = substr_matches[0]
            elif len(substr_matches) > 1:
                # Pick by most word overlap with blueprint title
                bp_words = set(n_name.split("-"))
                best_score = -1
                best_cand = None
                for s in substr_matches:
                    qf_t = qf_by_slug.get(s, {}).get("title", "")
                    qf_words = set(norm(qf_t).split("-"))
                    score = len(bp_words & qf_words)
                    if score > best_score:
                        best_score = score
                        best_cand = s
                if best_cand:
                    found = best_cand

        # 3. Code-based matching
        if not found:
            bp_codes = extract_codes(ecode) | extract_codes(ename) | extract_codes(exam_id)
            for code in sorted(bp_codes, key=len, reverse=True):
                if len(code) < 4:
                    continue
                candidates = qf_code_to_slugs.get(code, set())
                if len(candidates) == 1:
                    found = list(candidates)[0]
                    break
                elif len(candidates) > 1:
                    # Disambiguate: score each candidate by word overlap with BP title
                    bp_words = set(n_name.split("-")) - {
                        "the", "and", "of", "in", "for", "a", "an", "to", "on",
                    }
                    scored = []
                    for c in candidates:
                        qf_t = qf_by_slug.get(c, {}).get("title", "")
                        qf_words = set(norm(qf_t).split("-"))
                        overlap = len(bp_words & qf_words)
                        # Bonus: exact code in QF slug
                        code_in_slug = 1 if code in norm(c) else 0
                        scored.append((overlap + code_in_slug * 3, c))
                    scored.sort(key=lambda x: -x[0])
                    if scored and scored[0][0] >= 2:
                        # Only accept if clearly better than runner-up
                        if len(scored) == 1 or scored[0][0] > scored[1][0]:
                            found = scored[0][1]
                            break

        # 4. Alias matching
        if not found:
            for alias in alias_map.get(exam_id, []):
                n_a = norm(alias)
                if n_a in qf_by_norm_slug:
                    found = qf_by_norm_slug[n_a]
                    break
                if n_a in qf_by_norm_title:
                    found = qf_by_norm_title[n_a]
                    break
                for code in extract_codes(alias):
                    if len(code) >= 4:
                        cands = qf_code_to_slugs.get(code, set())
                        if len(cands) == 1:
                            found = list(cands)[0]
                            break
                if found:
                    break

        if found:
            matched[exam_id] = found
        else:
            unmatched_list.append((exam_id, ename, ecode, ebody))

    # Cross-vendor validation: remove suspect matches
    # Only remove if BOTH word overlap AND code overlap are zero
    qf_slug_to_title = {e["slug"]: e["title"] for e in qf_exams}
    stopwords = {
        "the", "and", "of", "in", "for", "a", "an", "to", "on",
    }
    removed = 0
    to_remove = []
    for eid in matched:
        bp_row = next((r for r in rows if r[0] == eid), None)
        if not bp_row:
            continue
        bp_name = bp_row[1] or ""
        bp_code = bp_row[2] or ""
        qf_title = qf_slug_to_title.get(matched[eid], "")
        qf_slug = matched[eid]

        # Check word overlap (liberal -- only remove basic stopwords)
        bp_words = set(norm(bp_name).split("-")) - stopwords
        qf_words = set(norm(qf_title).split("-")) - stopwords
        common_words = bp_words & qf_words

        # Check code overlap
        bp_codes = extract_codes(bp_code) | extract_codes(bp_name)
        qf_codes = extract_codes(qf_title) | extract_codes(qf_slug)
        common_codes = bp_codes & qf_codes

        # Only remove if NO word overlap AND NO code overlap AND enough words to judge
        if len(bp_words) >= 3 and len(common_words) == 0 and len(common_codes) == 0:
            to_remove.append(eid)
            removed += 1

    for eid in to_remove:
        bp_row = next((r for r in rows if r[0] == eid), None)
        unmatched_list.append((eid, bp_row[1] or "", bp_row[2] or "", bp_row[3] or ""))
        del matched[eid]

    print(f"Total blueprint exams: {len(rows)}")
    print(f"Matched: {len(matched)}")
    print(f"Removed (cross-vendor suspect): {removed}")
    print(f"Unmatched: {len(unmatched_list)}")
    print()

    # Spot checks
    print("=== SPOT CHECK ===")
    for eid in [
        "aws-cloud-practitioner-clf-c02",
        "comptia-security-plus-sy0-701",
        "microsoft-az-900-azure-fundamentals",
        "microsoft-az-104-azure-administrator",
        "google-cloud-professional-cloud-architect",
        "pmi-pmp",
        "isc2-cissp",
        "cisco-ccna-200-301",
        "ec-council-ceh-312-50",
        "servicenow-csa",
    ]:
        if eid in matched:
            qf_t = qf_slug_to_title.get(matched[eid], "?")
            print(f"  OK   {eid} -> {qf_t}")
        else:
            print(f"  MISS {eid}")

    print()
    print("=== UNMATCHED BY BODY (top 25) ===")
    body_counts = {}
    for eid, name, code, body in unmatched_list:
        body_counts[body] = body_counts.get(body, 0) + 1
    for body, count in sorted(body_counts.items(), key=lambda x: -x[1])[:25]:
        print(f"  {body}: {count}")

    print()
    print("=== SAMPLE UNMATCHED ===")
    for eid, name, code, body in unmatched_list[:30]:
        print(f"  [{body}] {name} ({code})")

    # Save
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(matched, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {OUT_PATH}: {len(matched)} mappings")


if __name__ == "__main__":
    main()
