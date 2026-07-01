"""
Greenhouse ATS - Public JSON API
Docs: https://developers.greenhouse.io/job-board.html
"""

import requests


def fetch_jobs(slug: str) -> list[dict]:
    """Fetch all active jobs from a Greenhouse job board."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "id": str(job["id"]),
                "title": job.get("title", ""),
                "location": job.get("location", {}).get("name", ""),
                "url": job.get("absolute_url", ""),
                "updated_at": job.get("updated_at", ""),
            })
        return jobs
    except requests.exceptions.HTTPError as e:
        print(f"  [Greenhouse:{slug}] HTTP error: {e}")
    except Exception as e:
        print(f"  [Greenhouse:{slug}] Error: {e}")
    return []
