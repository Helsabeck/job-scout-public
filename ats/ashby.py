"""
Ashby ATS - Public JSON API
Tries the newer posting-api endpoint first, falls back to the legacy v1 endpoint.
"""

import requests

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scout/1.0)",
}


def fetch_jobs(slug: str) -> list[dict]:
    """Fetch all active jobs from an Ashby job board."""

    # Try newer API endpoint first (POST to posting-api)
    jobs = _fetch_new_api(slug)
    if jobs is not None:
        return jobs

    # Fall back to legacy v1 endpoint
    jobs = _fetch_legacy_api(slug)
    if jobs is not None:
        return jobs

    print(f"  [Ashby:{slug}] Both API endpoints failed.")
    return []


def _fetch_new_api(slug: str) -> list[dict] | None:
    """
    Newer Ashby posting API.
    POST https://api.ashbyhq.com/posting-api/job-board.list
    """
    url = "https://api.ashbyhq.com/posting-api/job-board.list"
    payload = {"organizationHostedJobsPageName": slug}

    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("results", data.get("jobPostings", [])):
            if not job.get("isListed", True):
                continue
            job_id = job.get("id", "")
            jobs.append({
                "id": job_id,
                "title": job.get("title", ""),
                "location": job.get("locationName", job.get("location", "")),
                "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                "published_at": job.get("publishedAt", job.get("publishedDate", "")),
                "department": job.get("departmentName", ""),
            })
        return jobs
    except requests.exceptions.HTTPError:
        return None
    except Exception as e:
        print(f"  [Ashby:{slug}] New API error: {e}")
        return None


def _fetch_legacy_api(slug: str) -> list[dict] | None:
    """
    Legacy Ashby v1 endpoint.
    GET https://jobs.ashbyhq.com/{slug}/api/job-board/v1/json
    """
    url = f"https://jobs.ashbyhq.com/{slug}/api/job-board/v1/json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data.get("jobPostings", []):
            if not job.get("isListed", True):
                continue
            job_id = job.get("id", "")
            jobs.append({
                "id": job_id,
                "title": job.get("title", ""),
                "location": job.get("location", ""),
                "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                "published_at": job.get("publishedAt", job.get("publishedDate", "")),
                "department": job.get("departmentName", ""),
            })
        return jobs
    except requests.exceptions.HTTPError:
        return None
    except Exception as e:
        print(f"  [Ashby:{slug}] Legacy API error: {e}")
        return None
