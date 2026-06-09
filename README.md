# Local Job Radar

Local Job Radar is a local-first job discovery and tracking system for software roles involving C++, computer graphics, rendering, Unreal Engine, Vulkan, OpenGL, OpenXR, VR/XR, simulation, real-time 3D, game systems, and digital twins.

The system runs only when launched manually. It reads public job boards, normalizes and scores postings, stores every discovered job in SQLite, exports relevant jobs to Excel, generates a static website, and can publish updated results to GitHub Pages.

Live website: **https://lch9527.github.io/JobSearchSystem/**

## Goals

- Discover relevant technical jobs from public career boards.
- Keep a permanent local history without deleting old jobs automatically.
- Rank jobs against a graphics, Unreal, VR/XR, simulation, and C++ background.
- Preserve manually edited application status and notes.
- Provide both an Excel review workflow and a searchable static website.
- Run on demand with conservative request limits.
- Keep private local data out of the public website and Git repository.

## Non-Goals

The system does not:

- apply to jobs automatically;
- send email;
- modify resumes;
- use Google Sheets, Gmail, cloud databases, or a web application server;
- log into LinkedIn or other private job boards;
- bypass CAPTCHAs or authentication;
- delete old jobs automatically;
- publish private notes, descriptions, source payloads, SQLite, or Excel files.

## Architecture

```text
Public job boards
  Lever / Ashby / Greenhouse / HTML
                  |
                  v
        Collector implementations
                  |
                  v
     Normalize URL, text, and dates
                  |
                  v
      Stable hash and deduplication
                  |
                  v
       Keyword relevance scoring
                  |
                  v
       SQLite source of truth
        data/jobs.sqlite
          /       |       \
         v        v        v
      Excel    Website   Run logs
 job_radar.xlsx jobs.json job_radar.log
                   |
                   v
          Git commit and push
                   |
                   v
        GitHub Actions deployment
                   |
                   v
             GitHub Pages
```

## Complete Manual Workflow

Launch a search from the project directory:

```bash
scripts/run_and_publish.sh
```

Each manual launch performs this sequence:

1. The wrapper runs `main.py` with the project virtual environment.
2. `main.py` loads settings, sources, and keyword configuration.
3. Existing Excel `Status` and `Notes` values are imported into SQLite.
4. Every enabled source is queried sequentially with request limits and delays.
5. Each posting is normalized, hashed, scored, and upserted into SQLite.
6. One failed source is logged without stopping the remaining sources.
7. The Excel workbook is backed up and regenerated.
8. The public `docs/jobs.json` website feed is regenerated.
9. `scripts/publish_website.sh` checks for unrelated tracked changes.
10. If `docs/jobs.json` changed, it is committed and pushed to `main`.
11. The GitHub Pages workflow deploys the `docs/` directory.
12. The live website receives the updated results.

If no website data changed, no Git commit is created.

## Project Structure

```text
JobSearch/
├── main.py                         Main orchestration entry point
├── requirements.txt               Python runtime dependencies
├── README.md                      System design and operations guide
├── .env.example                   Optional local path overrides
├── config/
│   ├── settings.yaml              Paths, thresholds, and request limits
│   ├── sources.yaml               Public job board definitions
│   └── keywords.yaml              Matching weights and penalties
├── collectors/
│   ├── base.py                    Job model and HTTP behavior
│   ├── lever.py                   Lever public posting API
│   ├── ashby.py                   Ashby public job board API
│   ├── greenhouse.py              Greenhouse public board API
│   └── html_page.py               Configurable HTML link extraction
├── matching/
│   ├── scorer.py                  Relevance scoring and explanations
│   └── filters.py                 Score-based export filtering
├── storage/
│   ├── db.py                      SQLite schema and persistence
│   ├── models.py                  Status definitions
│   ├── excel_writer.py            Excel import/export and backups
│   └── web_writer.py              Privacy-filtered public JSON export
├── utils/
│   ├── config.py                  YAML and path handling
│   ├── hashing.py                 Stable job identity hashes
│   ├── logging.py                 Console and rotating file logs
│   ├── rate_limiter.py            Request delays and run limits
│   └── text.py                    Text, HTML, and URL normalization
├── scripts/
│   ├── run_and_publish.sh         Manual search/publish command
│   └── publish_website.sh         Guarded Git commit and push
├── docs/
│   ├── index.html                 Static website
│   ├── styles.css                 Responsive website styling
│   ├── app.js                     Browser filtering and rendering
│   ├── jobs.json                  Generated public job feed
│   └── .nojekyll                  Direct static Pages deployment
├── .github/workflows/pages.yml    GitHub Pages deployment
├── tests/                         Unit and integration tests
├── data/                          Local database, Excel, and backups
└── logs/                          Application logs
```

## Data Model and Persistence

SQLite at `data/jobs.sqlite` is the permanent source of truth.

### Jobs Table

The `jobs` table stores:

```text
id
job_hash
title
company
location
url
source_name
source_type
description
salary
employment_type
date_posted
date_found
last_seen
status
match_score
match_reason
notes
raw_data
created_at
updated_at
```

Additional tables:

- `run_logs`: run time, source count, discovered jobs, new jobs, errors, and duration.
- `source_checks`: latest check time and result for each configured source.

Indexes exist for status, score, company, last-seen time, and URL.

### Upsert Behavior

For a newly discovered job:

- a row is inserted;
- `date_found` and `last_seen` are set;
- status defaults to `New`.

For an existing job:

- current source fields, description, score, and `last_seen` are updated;
- the original `date_found` remains unchanged;
- user-managed `status` and `notes` are preserved.

Jobs are never automatically deleted.

## Deduplication

The primary identity is a SHA-256 `job_hash` generated from:

```text
normalized title + normalized company + normalized URL
```

When no URL exists, the fallback is:

```text
normalized title + normalized company + normalized location
```

A normalized URL is also used as a secondary database lookup.

Normalization includes:

- lowercase identity text;
- trimmed and collapsed whitespace;
- lowercase URL scheme and hostname;
- removal of fragments;
- removal of trailing slashes;
- removal of tracking parameters such as `utm_*`, `gh_src`, and `lever-source`.

## Collectors

All collectors implement the common `BaseCollector.fetch_jobs()` interface and return `Job` objects.

### Lever

Uses the public Lever postings API:

```text
https://api.lever.co/v0/postings/{company_slug}?mode=json
```

It extracts title, company, location, URL, description, salary, commitment, posting date, and raw source data.

### Ashby

Uses the public Ashby job board endpoint:

```text
https://api.ashbyhq.com/posting-api/job-board/{board_token}
```

It extracts board postings and converts HTML descriptions to plain text.

### Greenhouse

Uses the public Greenhouse board API:

```text
https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
```

It extracts title, location, URL, content, offices, and update time.

### Generic HTML

The HTML collector uses Requests and BeautifulSoup. Configuration can define:

```yaml
- name: Example Careers
  company: Example Company
  type: html
  url: https://example.com/careers
  enabled: true
  job_link_selector: "article.job"
  title_selector: "h2"
  location_selector: ".location"
  description_selector: ".summary"
```

Selectors other than `job_link_selector` are optional and evaluated inside each matching job element.

The collector only reads the configured public page. It does not execute JavaScript, authenticate, bypass CAPTCHAs, or recursively crawl arbitrary pages.

## Source Configuration

Sources are defined in `config/sources.yaml`.

Supported types:

```text
lever
ashby
greenhouse
html
```

Common fields:

```yaml
- name: Company Display Name
  company: Company Name
  type: lever
  company_slug: public-board-slug
  enabled: true
  notes: Optional source documentation.
```

The repository currently includes public boards targeting game development, rendering, robotics, simulation, CAD, XR, and C++ roles. Set `enabled: false` to stop querying a source without removing its history.

## Matching and Scoring

Matching configuration lives in `config/keywords.yaml`.

### Positive Rules

- A title boost keyword adds its configured weight when found in the title.
- An include keyword in the description adds its configured weight.
- An include keyword in the title adds `weight * 1.5`.

### Negative Rules

Exclude keywords subtract their configured penalty when found in the title or description.

### Final Score

```text
score = title boosts
      + title include matches * 1.5
      + description include matches
      - exclusion penalties
```

The final value is rounded and clamped to `0..100`.

The scorer also creates a human-readable `match_reason`, for example:

```text
Matched: title "Rendering Engineer" +30, "Vulkan" +15, "C++" +10
```

All parsed jobs are stored in SQLite. By default, only jobs scoring at least `35` are exported to Excel and the website.

## Excel Review Workflow

The generated workbook is:

```text
data/job_radar.xlsx
```

It contains five sheets:

- `Jobs`: matched postings and manual review fields.
- `Sources`: configured sources and latest check times.
- `Keywords`: matching terms, types, and weights.
- `Summary`: job status totals and run timing.
- `Run_Log`: recent run statistics and errors.

### Jobs Sheet

Visible columns include:

```text
Date Found
Last Seen
Status
Score
Title
Company
Location
Salary
Employment Type
Source
URL
Match Reason
Notes
```

`Job Hash` is stored in a hidden column for reliable synchronization.

Allowed statuses:

```text
New
Interested
Applied
Not Match
Rejected
Archived
```

### Status and Notes Preservation

At the start of every run:

1. the existing workbook is opened when present;
2. `Status` and `Notes` are read from each row;
3. rows are matched to SQLite by hidden job hash, with normalized URL fallback;
4. valid manual values are written into SQLite;
5. collector updates run without overwriting those fields;
6. the workbook is regenerated from SQLite.

Edit only `Status` and `Notes` for normal manual tracking.

### Workbook Backups

Before overwriting the workbook, the previous file is copied to:

```text
data/backups/job_radar_YYYYMMDD_HHMMSS_microseconds.xlsx
```

The latest 20 backups are retained by default.

If the main workbook cannot be replaced because another program has locked it, the exporter writes a timestamped fallback workbook instead of failing the entire run.

## Static Website

The website is a static client-side application in `docs/`.

It provides:

- free-text search;
- company filtering;
- status filtering;
- minimum score filtering;
- sorting by score, discovery date, company, or title;
- summary counts;
- responsive desktop and mobile layouts;
- direct links to employer postings.

No web server, cloud database, or JavaScript framework is required. GitHub Pages serves static HTML, CSS, JavaScript, and JSON.

### Public Data Boundary

`storage/web_writer.py` publishes only:

```text
title
company
location
url
source_name
source_type
salary
employment_type
date_posted
date_found
last_seen
status
match_score
match_reason
```

It explicitly excludes:

```text
notes
job_hash
description
raw_data
SQLite database
Excel workbook
local logs
```

The status is public on the website. Notes remain local and private.

## GitHub Pages Deployment

The website source is committed in `docs/`. `.github/workflows/pages.yml` runs when files under `docs/` or the workflow itself are pushed to `main`.

Deployment stages:

1. check out the repository;
2. configure GitHub Pages;
3. upload `docs/` as the Pages artifact;
4. deploy with `actions/deploy-pages`.

Live URL:

```text
https://lch9527.github.io/JobSearchSystem/
```

## Manual Git Publishing

`scripts/publish_website.sh` publishes generated website data safely.

Behavior:

- sets `GIT_TERMINAL_PROMPT=0` so a manual run fails instead of hanging for credentials;
- refuses to proceed when unrelated tracked changes are present;
- stages only `docs/jobs.json`;
- exits successfully without a commit when the file is unchanged;
- creates a timestamped commit when it changed;
- pushes `main` with a 60-second timeout;
- on initial push failure, runs `git pull --rebase origin main` and retries once.

This safeguard prevents a manual search from accidentally committing active source-code edits.

Untracked files do not block publication, and ignored local data remains uncommitted.

## Manual Launch

If an earlier version installed the systemd timer, disable and remove it once:

```bash
systemctl --user disable --now job-radar.timer
rm -f ~/.config/systemd/user/job-radar.timer ~/.config/systemd/user/job-radar.service
systemctl --user daemon-reload
```

Launch a search manually:

```bash
cd /home/lch9527/Desktop/JobSearch
scripts/run_and_publish.sh
```

Nothing in the repository schedules this command. Run it whenever you want to search and publish updated results.

## Error Handling and Exit Codes

One source failure does not stop other sources or local exports.

`main.py` exit codes:

```text
0  Run completed without source errors
1  Local outputs completed, but one or more sources failed
2  Fatal run failure
```

`run_and_publish.sh` publishes after exit `0` or `1`, because local outputs are valid in both cases. It does not publish after exit `2`.

Handled conditions include:

- network timeout;
- HTTP 403;
- HTTP 404;
- HTTP 429 with configured backoff;
- malformed source responses;
- missing source fields;
- unsupported source types;
- Excel file locks;
- SQLite lock timeout;
- Git push timeout or divergence;
- individual collector exceptions.

## Request Safety and Rate Limiting

The system queries enabled sources sequentially. Current defaults in `config/settings.yaml` include:

```yaml
requests:
  timeout_seconds: 20
  max_total_requests_per_run: 300

rate_limit:
  default_delay_min_seconds: 20
  default_delay_max_seconds: 60
  api_delay_min_seconds: 3
  api_delay_max_seconds: 10
  max_requests_per_domain_per_run: 10
  max_requests_per_api_source_per_run: 50
  backoff_seconds: [60, 120, 300, 600]
```

Rules:

- prefer public APIs;
- do not access authenticated pages;
- do not bypass anti-bot controls;
- do not retry forever;
- stop a source after request limits or HTTP errors;
- immediately back off after HTTP 429;
- continue safely when a source fails.

## Logging and Observability

Application logs are written to:

```text
logs/job_radar.log
```

Each run records:

- start and completion time;
- sources checked;
- jobs found;
- newly inserted jobs;
- source-specific errors;
- Excel and website export results;
- total duration.

Useful commands:

```bash
tail -n 100 logs/job_radar.log
```

## Installation

```bash
cd /home/lch9527/Desktop/JobSearch
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If Ubuntu reports that `ensurepip` is unavailable, install the matching `python3-venv` package first.

Optional path overrides can be placed in `.env`:

```bash
JOB_RADAR_DATABASE_PATH=data/jobs.sqlite
JOB_RADAR_EXCEL_PATH=data/job_radar.xlsx
JOB_RADAR_LOG_PATH=logs/job_radar.log
```

Relative paths resolve from the project root.

## Running Manually

Search and update local outputs only:

```bash
.venv/bin/python main.py
```

Search, update, commit changed website data, and push:

```bash
scripts/run_and_publish.sh
```

Publish an already generated `docs/jobs.json`:

```bash
scripts/publish_website.sh
```

Open Excel:

```bash
libreoffice --calc data/job_radar.xlsx
```

Preview the website locally:

```bash
.venv/bin/python -m http.server 8000 --directory docs
```

Then open:

```text
http://localhost:8000
```

## Configuration Reference

### `config/settings.yaml`

Controls:

- SQLite path;
- Excel path and score threshold;
- website output directory and score threshold;
- backup retention;
- log path and level;
- HTTP timeout and user agent;
- request limits and delays.

### `config/sources.yaml`

Controls:

- source name and company;
- collector type;
- public board slug/token or URL;
- enable/disable state;
- optional HTML selectors;
- operator notes.

### `config/keywords.yaml`

Controls:

- include keyword weights;
- title boost weights;
- exclusion penalties.

## Testing

Run all tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Current coverage includes:

- URL normalization;
- stable hash generation;
- location fallback identity;
- positive and negative scoring;
- rate-limit enforcement;
- SQLite insert and update behavior;
- low-score retention with export filtering;
- Excel status and notes round-trip preservation;
- public website field privacy.

Additional validation commands:

```bash
.venv/bin/python -m compileall -q main.py collectors matching storage utils tests
bash -n scripts/run_and_publish.sh scripts/publish_website.sh
node --check docs/app.js
```

## Troubleshooting

### Excel is empty

Check whether enabled sources returned jobs and whether jobs passed the score threshold:

```bash
tail -n 50 logs/job_radar.log
```

All parsed jobs remain in SQLite even when they are below the Excel threshold.

### Website did not update

Check whether the generated JSON changed:

```bash
git status --short docs/jobs.json
```

Run publication manually:

```bash
scripts/publish_website.sh
```

Then inspect the Pages workflow:

```text
https://github.com/lch9527/JobSearchSystem/actions
```

### Publishing reports unrelated changes

Commit, stash, or intentionally resolve tracked source-code edits. The publisher will not include them in a job-results commit.

### Source returns 403, 404, or 429

Disable or correct the source in `config/sources.yaml`. A source failure is isolated and does not remove previously stored jobs.

### LibreOffice locks the workbook

Close LibreOffice before a run when possible. The exporter will otherwise write a timestamped fallback workbook and log a warning.

### Git push fails

Confirm stored Git credentials and remote access:

```bash
git remote -v
git push
```

The publishing script cannot open an interactive credential prompt.

## Security and Privacy

- `.env`, virtual environments, databases, Excel files, backups, and logs are ignored by Git.
- Only privacy-filtered website data is committed.
- Employer URLs are restricted to HTTP or HTTPS by the website.
- No credentials are stored in repository files.
- Git authentication is provided by the local Git credential helper.
- Public job descriptions and raw API payloads remain local even though they originate from public boards.

## Maintenance Workflow

When changing source code:

1. make the change;
2. run the full test suite;
3. run syntax and unit validation;
4. commit and push the code;
5. manually run `scripts/run_and_publish.sh`;
6. verify the Pages workflow.

When adding a source:

1. identify the official public board type and token;
2. add it disabled to `config/sources.yaml`;
3. test it with a manual run;
4. inspect score quality and request volume;
5. enable it;
6. monitor logs after the first manual execution.

## License and Data Notice

This repository is a personal job-search automation project. Job postings belong to their respective employers and job board providers. The website links users to original employer postings; always verify availability, location, compensation, and requirements at the source before applying.
