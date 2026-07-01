#!/usr/bin/env python3
"""
scout.py - Job Scout main orchestrator
Run manually: python scout.py
Run on schedule: GitHub Actions (.github/workflows/weekly_scan.yml)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ats.greenhouse import fetch_jobs as greenhouse_fetch
from ats.lever import fetch_jobs as lever_fetch
from ats.ashby import fetch_jobs as ashby_fetch
from ats.workday import fetch_jobs as workday_fetch
from ats.icims import fetch_jobs as icims_fetch
from ats.successfactors import fetch_jobs as sf_fetch
from ats.workable import fetch_jobs as workable_fetch
from ats.scraper import fetch_jobs as scraper_fetch
from filter import keyword_prefilter, location_prefilter, score_jobs
from digest import build_html, send_email


SEEN_JOBS_FILE = Path("seen_jobs.json")
COMPANIES_FILE = Path("companies.yaml")


# ── Persistence ────────────────────────────────────────────────────────────────

def load_seen_jobs() -> dict:
    if SEEN_JOBS_FILE.exists():
        return json.loads(SEEN_JOBS_FILE.read_text())
    return {}


def save_seen_jobs(seen: dict) -> None:
    SEEN_JOBS_FILE.write_text(json.dumps(seen, indent=2, sort_keys=True))


def load_companies() -> list[dict]:
    with COMPANIES_FILE.open() as f:
        data = yaml.safe_load(f)
    return data["companies"]


# ── Fetching ───────────────────────────────────────────────────────────────────

def fetch_company_jobs(company: dict) -> tuple[list[dict], bool]:
    """
    Fetch jobs for a single company.
    Returns (jobs, success).
    """
    ats = company.get("ats", "custom")
    name = company["name"]
    jobs = []
    success = True

    try:
        if ats == "greenhouse":
            jobs = greenhouse_fetch(company["greenhouse_slug"])
        elif ats == "lever":
            jobs = lever_fetch(company["lever_slug"])
        elif ats == "ashby":
            jobs = ashby_fetch(company["ashby_slug"])
        elif ats == "workday":
            jobs = workday_fetch(
                company["workday_tenant"],
                company["workday_instance"],
                company.get("workday_job_board", "Jobs"),
            )
        elif ats == "icims":
            jobs = icims_fetch(company["icims_tenant"], company.get("career_url"))
        elif ats == "successfactors":
            jobs = sf_fetch(company["sf_company_id"])
        elif ats == "workable":
            jobs = workable_fetch(company["workable_slug"])
        else:
            # custom, jobvite, taleo, avature — use generic scraper
            jobs = scraper_fetch(company["career_url"], name)
    except Exception as e:
        print(f"  [Scout] Unexpected error fetching {name}: {e}")
        return [], False

    # Tag each job with company name
    for job in jobs:
        job["company"] = name

    if not jobs:
        success = False

    print(f"  {name}: {len(jobs)} jobs fetched {'✓' if jobs else '✗'}")
    return jobs, success


# ── New job detection ──────────────────────────────────────────────────────────

def find_new_jobs(all_jobs: list[dict], seen: dict) -> list[dict]:
    """Return jobs whose ID hasn't been seen before for their company."""
    new_jobs = []
    for job in all_jobs:
        company = job["company"]
        job_id = job.get("id", "").strip()
        if not job_id:
            continue
        if job_id not in seen.get(company, []):
            new_jobs.append(job)
    return new_jobs


def update_seen(seen: dict, all_jobs: list[dict]) -> dict:
    """Add all current job IDs to the seen dict."""
    for job in all_jobs:
        company = job["company"]
        job_id = job.get("id", "").strip()
        if not job_id:
            continue
        if company not in seen:
            seen[company] = []
        if job_id not in seen[company]:
            seen[company].append(job_id)
    return seen


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'='*60}")
    print(f"Job Scout starting at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    companies = load_companies()
    seen = load_seen_jobs()
    is_first_run = len(seen) == 0

    if is_first_run:
        print("⚡ First run detected — will initialize baseline and send confirmation email.\n")

    # ── 1. Fetch all jobs ──────────────────────────────────────────────────────
    print(f"[1/4] Fetching jobs from {len(companies)} companies...")
    all_jobs = []
    failed_companies = []

    for company in companies:
        jobs, success = fetch_company_jobs(company)
        all_jobs.extend(jobs)
        if not success:
            failed_companies.append(company["name"])

    print(f"\n  Total jobs fetched: {len(all_jobs)}")
    if failed_companies:
        print(f"  Failed to fetch: {', '.join(failed_companies)}")

    # ── 2. Find new jobs ───────────────────────────────────────────────────────
    print("\n[2/4] Finding new jobs...")
    new_jobs = find_new_jobs(all_jobs, seen)
    print(f"  New (not seen before): {len(new_jobs)}")

    # ── 3. Filter and score ────────────────────────────────────────────────────
    matched = []
    candidates = []
    if not is_first_run and new_jobs:
        print("\n[3/4] Filtering...")
        candidates = keyword_prefilter(new_jobs)
        print(f"  After keyword filter: {len(candidates)}")
        candidates = location_prefilter(candidates)
        print(f"  After location filter: {len(candidates)}")

        if candidates:
            print(f"  Scoring {len(candidates)} candidates with Claude API...")
            matched = score_jobs(candidates)
            print(f"  Matched: {len(matched)}")
        else:
            print("  No candidates passed filters.")
    else:
        print("\n[3/4] Skipping filter (first run or no new jobs).")

    # ── 4. Send email ──────────────────────────────────────────────────────────
    print("\n[4/4] Sending email digest...")
    run_date = datetime.now().strftime("%B %d, %Y")
    stats = {
        "fetched": len(all_jobs),
        "new": len(new_jobs),
        "candidates": len(candidates) if not is_first_run else 0,
        "matched": len(matched),
    }
    html = build_html(matched, failed_companies, run_date, is_first_run, stats=stats)
    send_email(html, len(matched), is_first_run)

    # ── 5. Save updated seen_jobs ──────────────────────────────────────────────
    seen = update_seen(seen, all_jobs)
    save_seen_jobs(seen)
    total_tracked = sum(len(v) for v in seen.values())
    print(f"\n  Saved seen_jobs.json ({total_tracked} total job IDs tracked)")

    print(f"\n{'='*60}")
    print("Job Scout complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
