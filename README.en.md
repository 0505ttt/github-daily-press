# GitHub Daily Press

**English** · [中文](README.md)

**A self-updating Chinese magazine of GitHub Trending, AI frontier news, and per-project dossiers — readable online, installable on your desktop, and fully offline-capable.**

Every morning at 08:30 (Beijing time), an automated pipeline scrapes GitHub Trending, collects AI news from ~10 sources, generates a fused daily issue (HTML), and files every project into a long-lived classified archive. Weekly and monthly digests are aggregated from local data. Everything is readable in one magazine interface — black & green, no account, no API key.

- **[Open the online magazine](https://0505ttt.github.io/github-daily-press/)** — no install, no sign-up
- **[Download the desktop app](https://github.com/0505ttt/github-daily-press/releases/latest)** — macOS (Intel & Apple Silicon) and Windows installers, offline reading
- The repo and content are in Chinese; the data pipeline, templates and tooling are fully open for inspection

## Highlights

- **Truly automated, every single day.** One scheduled task runs: scrape → parse → enrich via GitHub API → background research → generate HTML issue → update the project archive & index → rebuild the magazine. 96+ issues and counting.
- **A project archive, not just a feed.** Every repo that ever trends gets a dossier: first/last appearance, cumulative chart count, star history, category. 370+ projects classified into 12 categories and 130+ subcategories.
- **Honesty as a hard rule.** The pipeline never invents stars, repos or links. When GitHub returns 9 items instead of 10, the issue says so on its cover. Unavailable data is labeled "not retrieved".
- **Backfill without fabrication.** When the original scheduler was down for two months, 49 missing daily issues were rebuilt from Wayback Machine snapshots of `github.com/trending` — each backfilled issue carries a badge and its exact snapshot timestamp, 100% recoverable, 0% invented. (Details in the repo, in Chinese: `补档说明.md`)

## Three ways to use it

1. **Just read** — open the [online magazine](https://0505ttt.github.io/github-daily-press/). Nothing to install.
2. **Install the desktop app** — a clean, private reader from the [Releases](https://github.com/0505ttt/github-daily-press/releases) page. The app starts empty (no bundled history) and pulls content from this public repo or your own.
3. **Run your own pipeline** — the scraper, parser, templates and build scripts are in `tools/`. Point it at your own workspace and it becomes your personal intelligence system.

## Data policy

- All star counts, rankings and repo links are captured live from GitHub Trending or the GitHub API; news items always link their sources.
- Historical issues are immutable; corrections are noted in the repo, never silently rewritten.

## License

See [LICENSE](LICENSE). The magazine content is generated from public GitHub data and public news sources; each item links back to its origin.
