# Job Scout

Every weekday morning, Job Scout checks approximately 30 company career pages, finds postings that are new since the last check, filters them against my target roles, and emails me a digest of the matches. Each digest also shows the numbers behind it: how many postings were fetched, how many were new, how many made it through the filters, and how many matched.

I built it because checking that many career pages by hand wasn't something I could keep up with week after week. The scout does the checking. I spend my time on the roles worth a closer look.

## Results

I started building Job Scout in early May 2026.

- Monitors approximately 30 company career pages across eight applicant tracking systems.
- Has checked more than 20,000 unique job postings since launch.
- Matched roles feed an Excel scoring dashboard where I've evaluated 700+ roles on five weighted dimensions.
- Costs under $0.50 a week to run.

## What it does

1. Pulls the current job listings from each company's career site.
2. Compares them against the postings it has already seen, so only new ones move forward.
3. Drops titles that are clearly outside my target roles, using a keyword list. This step is free.
4. Drops postings outside the US and keeps local, remote, and US-based roles. Also free.
5. Sends what's left to the Claude API, which reads each posting's title, company, and location and gives a yes or no with a one-sentence reason.
6. Emails an HTML digest with the matched roles, their locations, the reason each one fits, and a summary of the run.
7. Saves the list of postings it has seen so the next run only looks at new ones. If Claude scoring fails for a batch, those postings stay unmarked and get another try on the next run.

The whole thing runs in GitHub Actions on a schedule. I don't maintain a server for it.

## Cost control: free filters first, AI scoring last

The only step that costs money is the Claude API call, so the scout runs the cheap filters first and only pays for what survives them.

**Keyword filter (free).** Checks each job title against include and exclude lists. Software engineering, sales, clinical, and similar titles are dropped before any API call.

**Location filter (free).** Drops postings in other countries. Keeps local, remote, and US-based roles. Postings with no location listed pass through, since a blank location often means remote.

**Claude API scoring (paid).** The remaining postings go to Claude in batches of 15 and get scored against a written profile of my background and target roles. At the volumes I see, this keeps the total under $0.50 a week.

This is a quick first pass. The roles it surfaces go into my Excel dashboard, where I score them in more depth.

## Email digest

Each digest includes:

- A run summary: postings fetched, postings new since the last run, postings that passed the keyword and location filters, and postings Claude matched.
- The matched roles, grouped by company, with title, location, and the reason each one fits.
- A list of any companies the scout couldn't reach, so I can check those pages myself.
- A warning if Claude scoring failed, so a quiet day never hides a broken run.

## Career sites it can read

Most companies post jobs through one of a handful of applicant tracking systems (ATS). Job Scout has a reader for each of these:

| ATS | How Job Scout reads listings | Notes |
|---|---|---|
| Greenhouse | Public job board API | Most reliable |
| Lever | Public job board API | Includes the original posting date |
| Ashby | Public job board API | Tries the current endpoint, then the older one |
| Workable | Public job board API | Common at smaller companies |
| Workday | Reads the same JSON feed the public career page loads | Up to 500 postings per company |
| SAP SuccessFactors | Reads the same JSON feed the public career page loads | Common at universities and large employers |
| iCIMS | Reads the public job search pages | Results vary by company setup |
| Custom, Taleo, Avature | Best-effort read of the career page | Often comes back empty; flagged in the digest for a manual check |

## Known limitations

- Taleo and Avature pages build their job lists with JavaScript, so the generic reader usually gets nothing back. Those companies show up in the digest's manual-check list.
- iCIMS setups differ from company to company. Some return full results and some return none.
- Workday and SuccessFactors readers depend on the JSON feed behind each company's career page. If a company changes how its career page is built, its entry in the config may need updating.
- Claude scores on title, company, and location only. It doesn't read the full job description. That's deliberate: it keeps cost down, and the detailed evaluation happens in my dashboard.
- The first run saves a baseline without scoring anything. Otherwise every open posting would look new and the first digest would be noise.

## Tech stack

Python 3.11 · `requests` · `beautifulsoup4` · `pyyaml` · `anthropic` · GitHub Actions · Gmail SMTP

---

# For anyone who wants to run it themselves

Everything below is setup and configuration detail.

## Project structure

```
job-scout/
├── .github/workflows/weekly_scan.yml   # Scheduled trigger
├── companies.yaml                       # Target companies and ATS settings
├── scout.py                             # Runs each step in order
├── filter.py                            # Keyword filter, location filter, Claude scoring
├── digest.py                            # Builds and sends the HTML email
├── seen_jobs.json                       # Job IDs already seen (updated each run)
└── ats/
    ├── greenhouse.py                    # Greenhouse job board API
    ├── lever.py                         # Lever job board API
    ├── ashby.py                         # Ashby job board API, with fallback
    ├── workday.py                       # Workday career page JSON feed
    ├── icims.py                         # iCIMS job search pages
    ├── successfactors.py                # SAP SuccessFactors career page JSON feed
    ├── workable.py                      # Workable job board API
    └── scraper.py                       # Generic reader for other career pages
```

## Setup

### Prerequisites

- A GitHub account (free)
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A Gmail account with an App Password ([myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))

### Steps

**1. Fork or clone this repo.** Keep your copy private, since your target company list lives in it.

**2. Add your target companies** to `companies.yaml`. See the configuration reference below.

**3. Update the fit profile** in `filter.py`:

- Edit `INCLUDE_KEYWORDS` and `EXCLUDE_KEYWORDS` for your target roles.
- Edit `LOCAL_TERMS` for your target geography.
- Edit `SYSTEM_PROMPT` to describe your background and the roles you want.

**4. Add GitHub Secrets** under Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GMAIL_APP_PASSWORD` | 16-character Gmail app password, no spaces |
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_RECIPIENT` | Where the digest should go |

**5. Run it once by hand** from Actions → Weekly Job Scout → Run workflow. This saves the baseline and sends a confirmation email. Real digests start with the next scheduled run.

## Configuration reference

### companies.yaml fields by ATS

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
  workday_instance: wd1              # wd1, wd3, wd5, wd12, etc. (from the URL)
  workday_job_board: JobBoardName    # path segment after /en-US/ in the URL

# iCIMS
- name: "Company Name"
  ats: icims
  icims_tenant: tenant-name          # subdomain before .icims.com (from the apply URL)
  career_url: "https://..."          # your browser's filtered search URL

# SAP SuccessFactors
- name: "Company Name"
  ats: successfactors
  sf_company_id: companyId           # from career4.successfactors.com/careers?company={id}

# Workable
- name: "Company Name"
  ats: workable
  workable_slug: company-slug        # from apply.workable.com/{slug}

# Custom, Taleo, Avature, Jobvite
- name: "Company Name"
  ats: custom
  career_url: "https://..."          # career page URL; best-effort reading
  notes: "Taleo, likely built with JavaScript; check manually if empty"
```

### Finding the ATS for a company

1. Open the company's career page in your browser.
2. Click into any job posting.
3. Look at the URL on the apply page. It almost always gives away the ATS:
   - `greenhouse.io` → Greenhouse
   - `lever.co` → Lever
   - `ashbyhq.com` → Ashby
   - `myworkdayjobs.com` → Workday
   - `.icims.com` → iCIMS
   - `successfactors.com` → SAP SuccessFactors
   - `workable.com` → Workable
   - `taleo.net` or `tbe.taleo.net` → Taleo (use `custom`; often built with JavaScript)
   - `avature.net`, or `meta-avature` in the page source → Avature (use `custom`; built with JavaScript)

## Customizing the filters

### Keyword filter

Edit `INCLUDE_KEYWORDS` and `EXCLUDE_KEYWORDS` in `filter.py`. This filter only looks at job titles, so keep terms short and likely to show up in a title. Exclude terms win over include terms.

### Location filter

Edit `FOREIGN_EXCLUDE_TERMS` to add countries or cities to drop, and `LOCAL_TERMS` to define your target geography. Postings with a blank location always pass.

### Claude scoring

Edit `SYSTEM_PROMPT` in `filter.py` to describe your background, the roles you want, and what to rule out. Plain English works. There's no special syntax.

## How the baseline works

`seen_jobs.json` stores `{company: [job_id_1, job_id_2, ...]}`. On each run:

- Any job ID not already in the list counts as new.
- After scoring and sending the email, the scout adds every current ID to the list. It never removes IDs.
- GitHub Actions commits the updated file back to the repo with `[skip ci]`.

**First run.** If the file is empty (`{}`), the scout saves a baseline without scoring and sends a confirmation email. Real digests start on the next run.

**Resetting the baseline.** To re-scan everything, set each company's list to `[]` but keep the company names. The scout will then score every current posting. If you clear the file to `{}` instead, the next run is treated as a first run and nothing gets scored.

## Scheduling

The scout runs Monday through Friday at 11:17 UTC. That's 7:17 AM ET during daylight saving time and 6:17 AM ET the rest of the year. To change it, edit the `cron` line in `.github/workflows/weekly_scan.yml`:

```yaml
- cron: '17 11 * * 1-5'   # minute hour day month weekday, in UTC
```

You can also start a run any time from Actions → Weekly Job Scout → Run workflow. Manual runs don't change the schedule.

## Costs

- **GitHub Actions:** free, well within the free tier.
- **Anthropic API:** under $0.50 a week. The cost depends on how many new postings get past the free filters.
- **Gmail:** free.

## License

MIT
