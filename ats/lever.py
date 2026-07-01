"""
Lever ATS - Public JSON API
Returns createdAt (ms since epoch) which is the actual posting date.
"""

import requests


def fetch_jobs(slug: str) -> list[dict]:
    """Fetch all active jobs from a Lever job board."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data:
            categories = job.get("categories", {})
            jobs.append({
                "id": job.get("id", ""),
                "title": job.get("text", ""),
                "location": categories.get("location", ""),
                "url": job.get("hostedUrl", ""),
                "created_at_ms": job.get("createdAt", 0),
                "team": categories.get("team", ""),
            })
        return jobs
    except requests.exceptions.HTTPError as e:
        print(f"  [Lever:{slug}] HTTP error: {e}")
    except Exception as e:
        print(f"  [Lever:{slug}] Error: {e}")
    return []
