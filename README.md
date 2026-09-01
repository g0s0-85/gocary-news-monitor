# GoCary News Monitor

Watches https://www.gocarylive.org/News for changes and logs them, hosted
entirely on GitHub (no server to run or pay for).

It doesn't scrape the rendered page — that page is filled in by JavaScript.
Instead it polls the same JSON API the site's own front end calls,
`https://www.gocarylive.org/News/GetAllNews`, diffs the result against the
last known snapshot, and records anything added, removed, or edited
(title, summary, routes, affected-routes flag, or publish date).

## How it works

- **`.github/workflows/check-news.yml`** — a GitHub Actions workflow that
  runs every 15 minutes, plus on demand. It runs `scripts/check_news.py`,
  and if anything changed, commits the update.
- **`scripts/check_news.py`** — fetches the news API, compares it to
  `docs/data/state.json`, and appends any changes to
  `docs/data/changelog.jsonl`.
- **`docs/index.html`** — a static dashboard (no backend) that reads those
  two files plus `docs/data/status.json` and renders the change log and the
  currently-published news. This is what GitHub Pages serves.

## One-time setup

1. **Create a GitHub repo** and push this folder to it:
   ```bash
   git init
   git add .
   git commit -m "Set up GoCary news monitor"
   git branch -M main
   git remote add origin https://github.com/<you>/gocary-news-monitor.git
   git push -u origin main
   ```
   (Swap in your own GitHub username/org and repo name. A public repo is
   fine here since GoCary's news feed is public information — that's also
   what lets you use GitHub Pages for free.)

2. **Let the workflow push commits.** In the repo on GitHub:
   `Settings → Actions → General → Workflow permissions` → select
   **"Read and write permissions"** → Save. Without this, the scheduled job
   can run the check but won't be able to commit the results.

3. **Turn on GitHub Pages.**
   `Settings → Pages` → under "Build and deployment", set **Source** to
   "Deploy from a branch", **Branch** to `main` and folder to **`/docs`** →
   Save. GitHub will give you a URL like
   `https://<you>.github.io/gocary-news-monitor/` — that's the link to
   share with colleagues.

4. **Kick off the first check** without waiting 15 minutes: in the repo, go
   to the **Actions** tab → "Check GoCary News" → **Run workflow**. That
   establishes the baseline snapshot; the dashboard will show "no changes
   logged yet" until something in the feed actually changes after that.

From then on it runs unattended — every 15 minutes GitHub Actions checks
the feed, and if anything changed, the dashboard updates automatically.

## Adjusting things

- **Check frequency**: edit the `cron` line in
  `.github/workflows/check-news.yml` (GitHub Actions schedules are
  best-effort and can lag a few minutes under load, but 15 min is reliable
  in practice).
- **What counts as a change**: edit `FIELDS_TO_COMPARE` in
  `scripts/check_news.py`.
