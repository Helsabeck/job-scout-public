# Job Scout 🔍

An automated job monitoring agent that runs every Monday morning, scans target company career pages for new postings, filters for relevant roles through a three-stage pipeline, and delivers a clean HTML email digest — including a run summary showing exactly how many jobs were fetched, filtered, and matched.

Built to solve a real problem: manually checking 20+ company career pages every week is tedious, inconsistent, and easy to let slip. This agent does it automatically, at scale, and only surfaces roles that actually match a defined profile.

---

## What It Does

1. **Fetches** current job listings from each target company via their ATS
2. **Compares** against a stored baseline to identify postings new since the last run
3. **Pre-filters by keyword** to eliminate obvious title mismatches (free)
4. **Pre-filters by location** to exclude foreign postings and keep local/remote roles (free)
5. **Scores** remaining candidates using the Claude API against a configurable fit profile
6. **Delivers** a formatted HTML email digest with matched roles, locations, fit rationale, and a pipeline summary
7. **Saves** the updated job ID baseline back to the repo for next week's comparison

Runs entirely in GitHub Actions — no server, no infrastructure, no ongoing maintenance.

---

## Architecture

```
job-scout/
├── .github/workflows/weekly_scan.yml   # Scheduled trigger (Monday 4 AM ET)
├── companies.yaml                       # Target companies + ATS configuration
├── scout.py                             # Main orchestrator
├── filter.py                            # Three-stage filtering (keyword + location + Claude API)
├── digest.py                            # HTML email builder + Gmail SMTP sender
├── seen_jobs.json                       # Persisted job ID baseline (auto-updated)
└── ats/
    ├── greenhouse.py                    # Greenhouse public JSON API
    ├── lever.py                         # Lever public JSON API
    ├── ashby.py                         # Ashby public JSON API (posting-api + v1 fallback)
    ├── workday.py                       # Workday internal JSON API
    ├── icims.py                         # iCIMS session-based HTML scraper
    ├── successfactors.py                # SAP SuccessFactors REST API
    ├── workable.py                      # Workable public JSON API
    └── scraper.py                       # Generic fallback scraper
```

---

## ATS Coverage

The agent handles eight ATS platforms, covering the most common systems used by employers:

| ATS | Approach | Public API? | Notes |
|---|---|---|---|
| Greenhouse | JSON API | ✅ Yes | Most reliable |
| Lever | JSON API | ✅ Yes | Includes `createdAt` date |
| Ashby | JSON API | ✅ Yes | Tries posting-api, falls back to v1 |
| Workable | JSON API | ✅ Yes | Common at SMBs |
| Workday | Internal endpoint | ⚠️ Unofficial | Stable, widely used |
| SAP SuccessFactors | REST API | ⚠️ Unofficial | Common at universities/enterprises |
| iCIMS | Session-based scraping | ❌ No | May require JavaScript |
| Custom / Taleo / Avature | Heuristic scraping | ❌ No | Best-effort only |

**Note on Taleo and Avature:** Both require JavaScript rendering to return job listings. The generic scraper makes a best-effort attempt but these typically return empty results. Companies using these platforms are flagged in the email digest as "check manually."

---

## Three-Stage Filtering

Filtering runs in stages to minimize Claude API costs while maintaining match quality.

**Stage 1 — Keyword pre-filter (free)**
Title-based keyword matching eliminates obvious mismatches (software engineers, sales roles, clinical positions, etc.) before any API calls.

**Stage 2 — Location pre-filter (free)**
Excludes postings in foreign countries; keeps local, remote, and US-based roles. Blank locations always pass (often indicates remote or unspecified).

**Stage 3 — Claude API scoring (paid)**
Remaining candidates are batched and scored against a configurable profile in `filter.py`. Each job gets a `YES/NO` judgment with a one-sentence rationale. At typical weekly volumes this costs well under $0.50/week.

---

## Email Digest

Each weekly email includes:
- A pipeline summary table (jobs fetched → new → keyword filter → location filter → matched)
- Matched roles with company, title, location, and fit rationale
- A warning section listing any companies that couldn't be reached

The matched count is green when roles are found, gray when there are none.

---

## Setup

### Prerequisites
- GitHub account (free)
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Gmail account with an App Password ([myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))

### Steps

**1. Fork or clone this repo** (keep it private — your target company list is in here)

**2. Configure your target companies** in `companies.yaml` (see Configuration Reference below)

**3. Update the fit profile** in `filter.py`:
- Edit `INCLUDE_KEYWORDS` and `EXCLUDE_KEYWORDS` for your target roles
- Edit `LOCAL_TERMS` in the location filter for your target geography
- Edit `SYSTEM_PROMPT` to describe your background and target roles

**4. Add GitHub Secrets** under Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GMAIL_APP_PASSWORD` | 16-character Gmail app password (no spaces) |
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_RECIPIENT` | Where to send the digest |

**5. Run manually once** via Actions → Weekly Job Scout → Run workflow to initialize the baseline. You'll receive a confirmation email. Real digests start the following Monday.

---

## Configuration Reference

### companies.yaml fields by ATS type

```yaml
# Greenhouse
- name: "Company Name"
  ats: greenhouse
  greenhouse_slug: company-slug      # from boards.greenhouse.io/{slug}

# Lever
- name: "Company Name"
  ats: lever
  lever_slug: company-slug           # from jobs.lever.co/{slug}

# Ashby
- name: "Company Name"
  ats: ashby
  ashby_slug: company-slug           # from jobs.ashbyhq.com/{slug}

# Workday
- name: "Company Name"
  ats: workday
  workday_tenant: tenant-name        # subdomain before .wd{N}.myworkdayjobs.com
  workday_instance: wd1              # wd1, wd3, wd5, wd12 etc — from the URL
  workday_job_board: JobBoardName    # path segment after /en-US/ in the URL

# iCIMS
- name: "Company Name"
  ats: icims
  icims_tenant: tenant-name          # subdomain before .icims.com (from apply URL)
  career_url: "https://..."          # your browser's filtered search URL

# SAP SuccessFactors
- name: "Company Name"
  ats: successfactors
  sf_company_id: companyId           # from: career4.successfactors.com/careers?company={id}

# Workable
- name: "Company Name"
  ats: workable
  workable_slug: company-slug        # from apply.workable.com/{slug}

# Custom / Taleo / Avature / Jobvite
- name: "Company Name"
  ats: custom
  career_url: "https://..."          # career page URL; best-effort scraping
  notes: "Taleo — likely JS-rendered; check manually if empty"
```

### Finding the ATS for any company

1. Open the company's career page in your browser
2. Click into any individual job posting
3. Check the URL on the apply page — it almost always reveals the ATS:
   - `greenhouse.io` → Greenhouse
   - `lever.co` → Lever
   - `ashbyhq.com` → Ashby
   - `myworkdayjobs.com` → Workday
   - `.icims.com` → iCIMS
   - `successfactors.com` → SAP SuccessFactors
   - `workable.com` → Workable
   - `taleo.net` or `tbe.taleo.net` → Taleo (custom scraper, often JS-rendered)
   - `avature.net` or `meta-avature` in page source → Avature (custom scraper, JS-rendered)

---

## Customizing the Filter

### Keyword filter (Stage 1)
Edit `INCLUDE_KEYWORDS` and `EXCLUDE_KEYWORDS` in `filter.py`. The keyword filter operates on job titles only, so keep terms short and likely to appear in titles.

### Location filter (Stage 2)
Edit `FOREIGN_EXCLUDE_TERMS` to add countries/cities to exclude, and `LOCAL_TERMS` to define your target geography. Blank locations always pass.

### Claude scoring (Stage 3)
Edit `SYSTEM_PROMPT` in `filter.py` to describe your background, target roles, and exclusion criteria. The prompt accepts any plain English description — no special syntax required.

---

## How the Baseline Works

`seen_jobs.json` stores a dict of `{company: [job_id_1, job_id_2, ...]}`. On each run:
- Job IDs not in the list are treated as new
- After scoring and sending the email, all current IDs are saved back
- GitHub Actions commits the updated file back to the repo with `[skip ci]`

**First run:** initializes the baseline without scoring — you receive a confirmation email only. Real digests start week two.

**Resetting the baseline:** To force a full re-scan, clear the job ID arrays in `seen_jobs.json` (keep the company keys but set each value to `[]`). This triggers scoring on all current jobs without triggering first-run mode.

---

## Scheduling

The default schedule is Monday at 9:00 AM UTC (4:00 AM ET winter / 5:00 AM ET summer). To change it, edit the `cron` line in `.github/workflows/weekly_scan.yml`:

```yaml
- cron: '0 9 * * 1'   # minute hour day month weekday (UTC)
```

You can also trigger a run manually at any time via Actions → Weekly Job Scout → Run workflow. Past scheduled runs don't affect the schedule — only the cron line does.

---

## Known Limitations

- **Taleo and Avature** career pages require JavaScript rendering. The generic scraper makes a best-effort attempt but these typically return empty results. Companies using these platforms appear in the "check manually" section of the digest.
- **iCIMS** varies by installation — some work well with session-based scraping, others block automated requests entirely.
- **Workday and SuccessFactors** use undocumented internal APIs that could change without notice. In practice these have been stable for years.
- **First run** initializes the baseline without scoring. This is intentional — on a first run, all current open jobs would appear "new," creating noise. The baseline prevents this from recurring.

---

## Costs

- **GitHub Actions**: Free (well within the free tier — ~5–10 minutes/week)
- **Anthropic API**: ~$0.05–$0.50/week depending on how many new jobs pass the keyword and location filters
- **Gmail**: Free

---

## Tech Stack

Python 3.11 · `requests` · `beautifulsoup4` · `pyyaml` · `anthropic` · GitHub Actions · Gmail SMTP

---

## License

MIT
