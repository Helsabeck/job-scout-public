"""
iCIMS ATS - HTML scraper
Uses the standard search URL without iframe mode, with session cookie priming.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_jobs(tenant: str, search_url: str = None) -> list[dict]:
    """
    Fetch jobs from an iCIMS job board.
    tenant:     subdomain e.g. 'globalcareers-sas'
    search_url: pre-filtered URL from companies.yaml (used as-is, no modifications)
    """
    base_url = f"https://{tenant}.icims.com"

    session = requests.Session()
    session.headers.update(HEADERS)

    # Prime session cookies by visiting the base domain first
    try:
        session.get(base_url, timeout=15)
    except Exception:
        pass

    # Use provided URL as-is, or fall back to plain search
    if search_url and tenant in search_url:
        base_search = search_url.rstrip("&")
    else:
        base_search = (
            f"{base_url}/jobs/search"
            "?ss=1&searchKeyword=&searchCategory="
            "&searchLocation=&searchZip=&searchRadius=30"
        )

    all_jobs = []
    page = 1

    while True:
        # iCIMS uses startIndex for pagination (25 per page)
        if "?" in base_search:
            paginated_url = f"{base_search}&startIndex={(page - 1) * 25}"
        else:
            paginated_url = f"{base_search}?startIndex={(page - 1) * 25}"

        try:
            resp = session.get(
                paginated_url,
                headers={"Referer": base_url},
                timeout=20,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"  [iCIMS:{tenant}] HTTP {e.response.status_code} on page {page}")
            break
        except Exception as e:
            print(f"  [iCIMS:{tenant}] Error on page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors — iCIMS markup varies by version
        job_links = (
            soup.select("a.iCIMS_Anchor")
            or soup.select("div.iCIMS_JobsTable a[href*='/jobs/']")
            or soup.select("a[href*='/jobs/'][class*='title']")
            or [
                a for a in soup.select("a[href*='/jobs/']")
                if a.get_text(strip=True) and len(a.get_text(strip=True)) > 5
            ]
        )

        if not job_links:
            break

        new_on_page = 0
        seen_ids = {j["id"] for j in all_jobs}

        for link in job_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not href or not text or "/jobs/" not in href:
                continue

            parts = href.split("/jobs/")
            if len(parts) < 2:
                continue
            job_id = parts[1].split("/")[0]

            if not job_id.isdigit() or job_id in seen_ids:
                continue

            full_url = href if href.startswith("http") else base_url + href
            all_jobs.append({
                "id": job_id,
                "title": text,
                "location": "",
                "url": full_url,
            })
            seen_ids.add(job_id)
            new_on_page += 1

        if new_on_page == 0 or len(all_jobs) >= 500:
            break

        page += 1

    return all_jobs
