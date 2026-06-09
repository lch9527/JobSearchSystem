# Local Job Radar

Local Job Radar collects public job postings, scores them for C++/graphics/VR/Unreal relevance, stores every result in SQLite, and exports matching jobs to an Excel workbook for manual tracking.

## Features

- Public Lever, Ashby, Greenhouse, and configurable HTML collectors
- Polite per-domain rate limiting and bounded requests
- Stable URL normalization and job deduplication
- Configurable 0-100 keyword scoring
- SQLite as the permanent source of truth
- Excel sheets: `Jobs`, `Sources`, `Keywords`, `Summary`, and `Run_Log`
- Round-trip preservation of manually edited `Status` and `Notes`
- Timestamped Excel backups, keeping the latest 20 by default
- Per-source error isolation and rotating local logs
- User-level systemd service and four-times-daily timer templates

## Setup

```bash
cd /home/lch9527/Desktop/JobSearch
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

The first run uses no network because all sample sources are disabled. It creates:

```text
data/jobs.sqlite
data/job_radar.xlsx
logs/job_radar.log
```

## Configure Sources

Edit `config/sources.yaml`. API collectors need the public board identifier:

```yaml
sources:
  - name: Example Studio
    company: Example Studio
    type: lever
    company_slug: example-studio
    enabled: true
```

For generic HTML pages, `job_link_selector` identifies each job link or job container. Optional `title_selector`, `location_selector`, and `description_selector` are evaluated inside that element:

```yaml
  - name: Example Careers
    company: Example
    type: html
    url: https://example.com/careers
    enabled: true
    job_link_selector: "article.job"
    title_selector: "h2"
    location_selector: ".location"
    description_selector: ".summary"
```

Only configure public pages that do not require authentication. The generic collector intentionally does not bypass CAPTCHAs or fetch private pages.

## Matching

Edit `config/keywords.yaml` to adjust positive title boosts, description/title keywords, and exclusions. All parsed jobs are retained in SQLite. Only jobs at or above `excel.minimum_export_score` in `config/settings.yaml` are exported to Excel.

## Excel Workflow

Open `data/job_radar.xlsx` and edit only `Status` and `Notes` in the `Jobs` sheet. Valid statuses are:

```text
New, Interested, Applied, Not Match, Rejected, Archived
```

At the beginning of each run, those values are imported into SQLite using the hidden `Job Hash` column, with normalized URL as fallback. Collector updates never overwrite them.

## Scheduling

Install the supplied units as user services, which avoids root-owned output files:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/job-radar.service systemd/job-radar.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now job-radar.timer
systemctl --user list-timers job-radar.timer
```

Manual run and logs:

```bash
systemctl --user start job-radar.service
journalctl --user -u job-radar.service -n 100 --no-pager
```

The timer runs at local time at `09:00`, `12:00`, `16:00`, and `20:00`, and catches up after downtime because `Persistent=true`.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Configuration Files

- `config/settings.yaml`: paths, export threshold, requests, delays, and schedule metadata
- `config/sources.yaml`: source definitions and enable flags
- `config/keywords.yaml`: matching weights and penalties
- `.env.example`: optional path overrides

Request limits are intentionally conservative. A failed source is logged and does not prevent remaining sources or the Excel export from running.

## GitHub Pages Website

Each successful `main.py` run regenerates `docs/jobs.json` from SQLite. The public file includes job details, score, status, and application URL, but excludes notes, hashes, descriptions, and raw source data.

Preview locally:

```bash
.venv/bin/python -c "from pathlib import Path; from storage.db import Database; from storage.web_writer import export_website; db=Database(Path('data/jobs.sqlite')); export_website(db, Path('docs'), 35); db.close()"
.venv/bin/python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`.

The workflow in `.github/workflows/pages.yml` deploys `docs/` to GitHub Pages whenever website files are pushed to `main`. The expected URL is:

```text
https://lch9527.github.io/JobSearchSystem/
```

After a local scheduled search refreshes the site data, publish it with:

```bash
git add docs/jobs.json
git commit -m "Update job results"
git push
```
