"""
Workday ATS - Internal JSON API (undocumented but stable)
Pagination handled automatically; pulls up to 500 jobs per company.
"""

import requests


HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scout/1.0)",
}


def fetch_jobs(tenant: str, instance: str, job_board: str = "Jobs") -> list[dict]:
    """
    Fetch jobs from a Workday instance.
    tenant: e.g. 'iqvia'
    instance: e.g. 'wd1'
    job_board: path segment after /en-US/ in the career URL
    """
    base_url = (
        f"https://{tenant}.{instance}.myworkdayjobs.com"
        f"/wday/cxs/{tenant}/{job_board}/jobs"
    )

    all_jobs = []
    offset = 0
    limit = 20  # Workday default page size

    while True:
        payload = {
            "appliedFacets": {},
            "limit": limit,
            "offset": offset,
            "searchText": "",
        }
        try:
            resp = requests.post(
                base_url, json=payload, headers=HEADERS, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"  [Workday:{tenant}] HTTP {e.response.status_code} — "
                  f"job_board '{job_board}' may be wrong. Check the URL.")
            break
        except Exception as e:
            print(f"  [Workday:{tenant}] Error: {e}")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break

        for job in postings:
            external_path = job.get("externalPath", "")
            job_url = (
                f"https://{tenant}.{instance}.myworkdayjobs.com"
                f"/en-US/{job_board}{external_path}"
            )
            # Use externalPath as ID since it's stable
            job_id = external_path.strip("/").replace("/", "_") or job.get("title", "")
            all_jobs.append({
                "id": job_id,
                "title": job.get("title", ""),
                "location": job.get("locationsText", ""),
                "url": job_url,
                "posted_on": job.get("postedOn", ""),  # e.g. "Posted 3 Days Ago"
            })

        # Check if more pages exist
        total = data.get("total", 0)
        offset += limit
        if offset >= total or offset >= 500:  # safety cap
            break

    return all_jobs
