"""
SAP SuccessFactors ATS - Internal JSON API
Uses the undocumented but stable job search endpoint.
Confirmed working for: Duke University (dukeuniverP1)
"""

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*",
    "Referer": "https://career4.successfactors.com/",
}


def fetch_jobs(company_id: str) -> list[dict]:
    """
    Fetch jobs from a SuccessFactors job board.
    company_id: e.g. 'dukeuniverP1'
    """
    url = (
        f"https://career4.successfactors.com/restapi/jobsearch/v2"
        f"?company={company_id}&lang=en_US&country=US&start=0&count=100"
    )

    all_jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        for job in data.get("jobs", []):
            job_id = str(job.get("jobId", "") or job.get("id", ""))
            title = job.get("jobTitle", "") or job.get("title", "")
            location = job.get("location", "") or job.get("city", "")
            job_url = (
                f"https://career4.successfactors.com/careers?company={company_id}"
                f"&jobId={job_id}"
            )
            if job_id and title:
                all_jobs.append({
                    "id": job_id,
                    "title": title,
                    "location": location,
                    "url": job_url,
                })

    except requests.exceptions.HTTPError as e:
        print(f"  [SuccessFactors:{company_id}] HTTP error: {e} — "
              f"API endpoint may have changed.")
    except ValueError:
        # Response wasn't JSON — likely JS-rendered, fall back gracefully
        print(f"  [SuccessFactors:{company_id}] Non-JSON response — "
              f"site may require JavaScript. Check manually.")
    except Exception as e:
        print(f"  [SuccessFactors:{company_id}] Error: {e}")

    return all_jobs
