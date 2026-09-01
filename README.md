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
  runs `scripts/check_news.py` and, if anything changed, commits the
  update. It's triggered by `workflow_dispatch` (an API call anyone with
  write access can make, including a script) rather than GitHub's own
  `schedule:` trigger — that's still in the file, but GitHub's built-in
  cron turned out to be too unreliable on this repo (over 2 hours between
  its first two fires), so it's not what's actually driving checks.
- **A [cron-job.org](https://cron-job.org) job** (set up separately, not
  part of this repo) calls GitHub's API once a minute to fire that
  `workflow_dispatch` event — this is what actually keeps the checks
  running on schedule. It needs a GitHub personal access token (fine-
  grained, scoped to just this repo, with "Actions: Read and write"
  permission) in its Authorization header.
- **`scripts/check_news.py`** — fetches the news API, compares it to
  `docs/data/state.json`, and appends any changes to
  `docs/data/changelog.jsonl`.
- **`docs/index.html`** — a static dashboard (no backend) that reads those
  two files plus `docs/data/status.json` and renders the change log and the
  currently-published news (pinned above the log). This is what GitHub
  Pages serves. It reads the data via the GitHub Contents API rather than
  fetching `data/*.json` directly — GitHub Pages fronts those files with a
  CDN that caches for 10 minutes and ignores query strings, so a plain
  fetch (even with a cache-busting `?t=`) can silently serve stale data.
  The Contents API caches for only 60 seconds; if a call to it fails (e.g.
  its 60-requests/hour-per-IP unauthenticated rate limit), the page falls
  back to fetching the Pages-served copy directly, which may then lag.

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

5. **Set up the external trigger** (see "How it works" above) — create a
   fine-grained GitHub token scoped to this repo with "Actions: Read and
   write" permission, and a free cron-job.org job that POSTs to
   `https://api.github.com/repos/<you>/gocary-news-monitor/actions/workflows/check-news.yml/dispatches`
   with that token in an `Authorization: Bearer <token>` header and body
   `{"ref":"main"}`. Without this, checks only happen when someone clicks
   "Run workflow" by hand.

From then on it runs unattended — cron-job.org checks the feed every
minute, and if anything changed, the dashboard updates automatically.

## Adjusting things

- **Check frequency**: change the schedule on the cron-job.org job (it's
  what actually controls timing now, not the `cron:` line in
  `check-news.yml`). Any change that's added and then reverted entirely
  between two checks will never show up in the log, no matter how tight
  the interval.
- **What counts as a change**: edit `FIELDS_TO_COMPARE` in
  `scripts/check_news.py`.
