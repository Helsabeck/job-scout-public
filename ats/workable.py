"""
Workable ATS - Public JSON API
Confirmed working for: Eton Solutions (eton-solutions)
API docs: https://workable.com/api
"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scout/1.0)",
    "Accept": "application/json",
}


def fetch_jobs(slug: str) -> list[dict]:
    """
    Fetch jobs from a Workable job board.
    slug: company slug from apply.workable.com/{slug}
    """
    url = (
        f"https://apply.workable.com/api/v1/widget/accounts/{slug}/vacancies"
        "?details=true&lang=en"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []

        for job in data.get("results", []):
            job_id = job.get("shortcode", job.get("id", ""))
            title = job.get("title", "")
            location_parts = [
                job.get("city", ""),
                job.get("state", ""),
                job.get("country", ""),
            ]
            location = ", ".join(p for p in location_parts if p)

            if not job_id or not title:
                continue

            jobs.append({
                "id": str(job_id),
                "title": title,
                "location": location,
                "url": f"https://apply.workable.com/{slug}/j/{job_id}/",
                "department": job.get("department", ""),
                "remote": job.get("remote", False),
            })

        return jobs

    except requests.exceptions.HTTPError as e:
        print(f"  [Workable:{slug}] HTTP error: {e}")
    except Exception as e:
        print(f"  [Workable:{slug}] Error: {e}")

    return []
