"""
Generic scraper for Jobvite-powered pages and custom career portals.
Extracts job links using heuristic selectors. Best-effort: these sites
may block bots or require JavaScript. Failures are logged gracefully.
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# CSS selectors that tend to contain job listing links across common frameworks
JOB_LINK_SELECTORS = [
    "a[href*='job']",
    "a[href*='career']",
    "a[href*='position']",
    "a[href*='opening']",
    ".job-title a",
    ".position-title a",
    "h3 a",
    "h4 a",
]

# Terms in link text that suggest it's an actual job posting
JOB_TITLE_SIGNALS = [
    "analyst", "manager", "director", "engineer", "specialist",
    "consultant", "coordinator", "lead", "senior", "associate",
    "architect", "developer", "scientist", "advisor", "officer",
]

# Terms in URLs that suggest it's a job detail page
JOB_URL_SIGNALS = [
    "/job/", "/jobs/", "/career/", "/careers/", "/position/",
    "/opening/", "/requisition/", "jobid=", "req_id=",
]


def looks_like_job_link(href: str, text: str) -> bool:
    """Heuristic: is this link likely a job posting?"""
    href_lower = href.lower()
    text_lower = text.lower().strip()

    if not text_lower or len(text_lower) < 5:
        return False
    if any(signal in href_lower for signal in JOB_URL_SIGNALS):
        return True
    if any(signal in text_lower for signal in JOB_TITLE_SIGNALS):
        return True
    return False


def fetch_jobs(career_url: str, company_name: str = "") -> list[dict]:
    """
    Scrape a career page for job listings.
    Returns list of job dicts on best-effort basis.
    """
    try:
        resp = requests.get(career_url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        print(f"  [Scraper:{company_name}] HTTP {status} — site may block bots. "
              f"Check manually: {career_url}")
        return []
    except Exception as e:
        print(f"  [Scraper:{company_name}] Could not reach site: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    seen_hrefs = set()
    jobs = []

    for selector in JOB_LINK_SELECTORS:
        for link in soup.select(selector):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not href or href in seen_hrefs:
                continue
            if not looks_like_job_link(href, text):
                continue

            # Resolve relative URLs
            full_url = urljoin(career_url, href)
            seen_hrefs.add(href)

            # Use URL hash or last path segment as ID
            job_id = re.sub(r"[^a-zA-Z0-9_-]", "_", href)[-80:]

            jobs.append({
                "id": job_id,
                "title": text[:200],
                "location": "",
                "url": full_url,
            })

    if not jobs:
        print(f"  [Scraper:{company_name}] No jobs found at {career_url} — "
              f"site may require JavaScript. Check manually.")

    return jobs
