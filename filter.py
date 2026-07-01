"""
filter.py - Three-stage job filtering
Stage 1: Keyword pre-filter (free — eliminates obvious title mismatches)
Stage 2: Location pre-filter (free — excludes foreign countries, keeps RTP/remote/US)
Stage 3: Claude API scoring (paid — quality matching against your profile)
"""

import json
import os
import anthropic


# ── Stage 1: Keyword Pre-filter ───────────────────────────────────────────────

# Job titles containing ANY of these → keep for Claude review
INCLUDE_KEYWORDS = [
    "analytic", "analyst", "analysis", "intelligence",
    "power bi", "tableau", "dashboard", "reporting", "report",
    "data ", " data", "sql", "visualization",
    "program manager", "programme manager", "project manager",
    "pmo", "portfolio", "governance",
    "business operations", "biz ops", "bizops", "strategy",
    "transformation", "process improvement", "process excellence",
    "operations manager", "operations lead",
    "business analyst", "systems analyst",
    "m365", "power platform", "sharepoint", "automation",
    "metrics", "kpi", "insights manager",
    "it manager", "technology manager",
    "scrum master", "delivery manager",
]

# Job titles containing ANY of these → exclude immediately (saves API calls)
EXCLUDE_KEYWORDS = [
    "software engineer", "software developer",
    "full stack", "fullstack", "front end", "frontend", "back end", "backend",
    "devops", "site reliability", "sre ", "infrastructure engineer",
    "mobile engineer", "ios engineer", "android engineer",
    "machine learning engineer", "ml engineer", "ai engineer",
    "sales ", "account executive", "account manager",
    "customer success", "customer support", "customer service",
    "marketing", "brand manager", "content manager", "seo",
    "nurse", "physician", "pharmacist", "clinician", "therapist",
    "attorney", "lawyer", "paralegal",
    "accountant", "cpa ", "financial advisor", "wealth advisor",
    "truck driver", "warehouse", "forklift",
    "intern ", "internship", "electrician", "social worker",
]


def keyword_prefilter(jobs: list[dict]) -> list[dict]:
    """
    Fast keyword check on job title.
    Returns jobs that pass (potentially relevant) for location and Claude scoring.
    """
    passed = []
    for job in jobs:
        title = job.get("title", "").lower()

        # Hard exclude first
        if any(kw in title for kw in EXCLUDE_KEYWORDS):
            continue

        # Must match at least one include keyword
        if any(kw in title for kw in INCLUDE_KEYWORDS):
            passed.append(job)

    return passed


# ── Stage 2: Location Pre-filter ──────────────────────────────────────────────

# Locations containing ANY of these → exclude (foreign postings)
FOREIGN_EXCLUDE_TERMS = [
    "india", "bangalore", "bengaluru", "hyderabad", "mumbai", "pune",
    "chennai", "delhi", "gurugram", "noida",
    "canada", "toronto", "vancouver", "montreal",
    "united kingdom", "london", "manchester",
    "australia", "sydney", "melbourne",
    "germany", "berlin", "munich",
    "france", "paris",
    "singapore", "ireland", "dublin",
    "mexico", "brazil", "argentina",
    "philippines", "manila",
]

# Locations containing ANY of these → keep (local or remote)
# Customize this list for your target geography
LOCAL_TERMS = [
    "raleigh", "cary", "durham", "chapel hill", "morrisville",
    "apex", "garner", "wendell", "holly springs", "clayton",
    "research triangle", "research triangle park", "rtp",
    "wake county", "durham county", "orange county",
    "north carolina", ", nc",
    "remote", "work from home", "wfh", "virtual", "anywhere",
    "united states", "usa",
]


def location_prefilter(jobs: list[dict]) -> list[dict]:
    """
    Keep jobs that are local, remote, US-based, or have no location specified.
    Explicitly exclude known foreign locations.
    Blank locations always pass (often indicates remote or unspecified).
    """
    passed = []
    for job in jobs:
        location = job.get("location", "").lower().strip()

        # Always pass blank locations
        if not location:
            passed.append(job)
            continue

        # Hard exclude known foreign locations
        if any(term in location for term in FOREIGN_EXCLUDE_TERMS):
            continue

        # Pass local, remote, and US-based locations
        if any(term in location for term in LOCAL_TERMS):
            passed.append(job)

    return passed


# ── Stage 3: Claude API Scoring ───────────────────────────────────────────────

# Customize this prompt to match your background and target roles
SYSTEM_PROMPT = """You are evaluating job postings for a candidate with the following profile:

BACKGROUND:
- 16 years of experience in Business Intelligence and Program Management
- Expert: Power BI (DAX, Power Query, semantic models, RLS), Power Automate, Power Apps, Excel/VBA, SharePoint, Azure DevOps
- Proficient: SQL (moderate), Python (actively upskilling), Copilot Studio
- No experience with: Snowflake, Databricks, dbt, Spark
- Program management: Led workstreams on enterprise programs ($12M–$191M budgets), cross-functional stakeholder management, executive-level advisory
- AI governance: Built and maintained tracking/reporting platform for 150+ AI use cases
- Domain: Financial services, HR transformation, procurement, workforce analytics

MATCH CRITERIA — say YES if the role involves any of the following at Senior/Lead/Manager/Director/Principal IC level:
- Business Intelligence, data analytics, reporting, or dashboard development
- Program or project management, especially enterprise-scale or cross-functional
- Business operations, strategy & operations, or transformation with data/technology emphasis
- Power Platform, M365, or automation/governance in an analytical capacity
- Data governance, portfolio management, or PMO roles
- Process improvement with analytical or technology components
- Hybrid roles that bridge business and technical teams

SAY NO if:
- Pure software engineering, development, or SRE
- Sales, account management, customer success, marketing
- Clinical, medical, legal, or licensed-profession roles
- Entry-level (clearly < 3 years experience required)
- Requires tools the candidate has zero experience with as the PRIMARY requirement

Be inclusive — if there's a plausible 60%+ qualification fit, say YES.

Respond ONLY with a JSON array, one object per job, in the same order received:
[{"fit": "YES", "reason": "brief reason"}, {"fit": "NO", "reason": "brief reason"}, ...]"""


def score_jobs(jobs: list[dict]) -> list[dict]:
    """
    Score jobs with Claude API. Returns only YES matches with fit_reason added.
    Processes in batches of 15 to balance latency and API cost.
    """
    if not jobs:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [Filter] ANTHROPIC_API_KEY not set — skipping Claude scoring.")
        return jobs

    client = anthropic.Anthropic(api_key=api_key)
    matched = []
    batch_size = 15

    for batch_start in range(0, len(jobs), batch_size):
        batch = jobs[batch_start: batch_start + batch_size]

        lines = []
        for i, job in enumerate(batch, 1):
            lines.append(
                f"{i}. {job.get('title', 'Unknown')} "
                f"at {job.get('company', 'Unknown')} "
                f"({job.get('location', 'location unknown')})"
            )
        job_list = "\n".join(lines)

        try:
            resp = client.messages.create(
                model="claude-sonnet-5",
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Evaluate these {len(batch)} job postings:\n\n{job_list}",
                    }
                ],
            )

            raw = resp.content[0].text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            results = json.loads(raw.strip())

            for i, result in enumerate(results):
                if i >= len(batch):
                    break
                if result.get("fit") == "YES":
                    job = batch[i].copy()
                    job["fit_reason"] = result.get("reason", "")
                    matched.append(job)

        except json.JSONDecodeError as e:
            print(f"  [Filter] JSON parse error on batch {batch_start}: {e}")
        except Exception as e:
            print(f"  [Filter] API error on batch {batch_start}: {e}")

    return matched
