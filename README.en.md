# GitHub Daily Press

**English** · [中文](README.md)

![GitHub Daily Press: open-source trends, read like a magazine](docs/images/项目封面.svg)

**A Chinese-language magazine built from GitHub Trending, AI frontier news, and per-project dossiers — readable online, installable on your desktop, with offline reading once pages are cached.**

Every item links back to its source. The interface, the issues and the repo are in Chinese; the pipeline, templates and tooling are fully open for inspection, so you can audit the code even if you don't read the articles.

- **[Open the online magazine](https://0505ttt.github.io/github-daily-press/)** — no install, no account, no API key. It shows the latest published issue; it is a published page, not a live feed that re-scrapes Trending.
- **[Download the desktop app](https://github.com/0505ttt/github-daily-press/releases/latest)** — macOS (Intel & Apple Silicon) and Windows installers, plus a source ZIP for running and modifying it yourself.
- Docs in the repo are written in Chinese; links below are labeled as such.

## What's inside

Counts are as of late October 2026 and grow as new issues are published.

- **Daily GitHub Trending issues.** 98 daily issues (+2 weekly digests) published between 2026-07-10 and late October 2026; about half were backfilled. Each issue has a trend summary, per-project intros, and the ranked list with that day's star changes.
- **A project archive, not just a feed.** 380+ dossiers covering every repo that ever trended: first and last appearance, cumulative chart count, stars recorded at each appearance, classified into 11 categories and 180+ subcategories.
- **An AI news digest with visible sources.** A configured LLM fuses material collected from 12 sources (vendor blogs, Hugging Face papers, tech media, and more); every item links back to its origin. Thin days publish fewer items instead of padding.
- **Honesty rules enforced in code.** Rankings and stars come from real Trending pages and the GitHub API. When GitHub returns 9 entries instead of 10, the issue says so on its cover. Missing data is labeled, never invented.
- **Backfill without fabrication.** 50 issues missed by the original run were rebuilt from Wayback Machine snapshots of `github.com/trending`. Each carries a backfill badge, its exact snapshot timestamp and link. Snapshot stars reflect that moment, not today. (Details in `补档说明.md`, Chinese.)

## How updates actually work

**The maintainer's editorial run and your reading are two separate things.** Today, the public site updates when the maintainer finishes an editorial run and pushes the checked result here; GitHub Pages then serves it. Run times vary from day to day — treat this as a daily-updated magazine, not a real-time service with a guaranteed clock time.

The repo also ships the automation, so *your* content can be produced without your machine staying on. [`.github/workflows/daily.yml`](.github/workflows/daily.yml) provides:

- a scheduled run at **08:30 Beijing time** (00:30 UTC); Mondays add a weekly digest, and the 1st of a month aggregates the previous month into a monthly digest;
- an **`ENABLE_DAILY` repo-variable gate** — production runs only happen after you set it to `true` under your repo's Settings → Secrets and variables → Actions → Variables;
- a manual trigger (`workflow_dispatch`): `validate` writes to a temporary branch and deletes it afterwards; `production` updates the default branch;
- honest failure handling: GitHub's scheduler can start runs late, and failed sub-tasks keep the last valid content instead of overwriting it.

Cloud runs need model credentials in repo Secrets (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`). GitHub's cloud runner cannot reach an Ollama instance on your desktop. Details: [云端自动更新](docs/云端自动更新.md) (Chinese).

## Three ways to use it

1. **Just read** — open the [online magazine](https://0505ttt.github.io/github-daily-press/). Nothing to install. For offline reading, install it as a PWA and wait for the "ready for offline" status; cached pages stay readable without a network.
2. **Install the desktop app, or run from source** — pick a file from [Releases](https://github.com/0505ttt/github-daily-press/releases): installers are for daily use, the source ZIP for running and modifying. Source runs need Python 3.11+ (`启动.command` on macOS, `启动.bat` on Windows) and open `http://127.0.0.1:8765/`.

   **The local app starts as a blank personal workspace and syncs nothing by default.** It does not bundle the maintainer's history. Syncing is opt-in: in Settings, enter `owner/repository` and press "Sync now" — point it at this public repo to read its published issues, or at your own repo to carry content across devices (default branch: `main`). Syncing updates reading content only; your local code and settings stay untouched. Your first self-generated issue becomes issue 001, and issues keep counting up.
3. **Bring your own AI tools** — if you already use ZCode, Claude Code, Hermes, Kimi Code or similar, let them write issues and dossiers into your workspace (`python -m gh_daily workspace` shows where). No separate API key for this project is needed. Playbook: [AI工具采编](docs/AI工具采编.md) (Chinese).

## Model configuration

Only generating content needs a model. Reading — online or offline — needs none, and the public reading site has no key input. In your local app: Tools → Settings → Model connection, then test the connection and save.

| Option | You provide |
| --- | --- |
| OpenAI-compatible endpoint | API URL, API key, model name (HTTPS enforced for cloud endpoints) |
| Local Ollama | A running Ollama, its local address, and a downloaded model name — no key |

Timeout and output limits are adjustable. Keys are saved only in your user config directory, are not echoed back after saving, and are never written into public pages or the reading cache. Details: [安装与模型设置](docs/安装与模型设置.md) (Chinese).

## Data policy

- Rankings and stars are captured live from GitHub Trending or the GitHub API; news items always link their sources. Editorial rules added on 2026-10-26 require per-item source verification for new issues before publishing.
- **History is traceable, not immutable.** Published content is versioned in Git: corrections to old issues do happen, and they land as new, auditable commits — the 2026-10-26 AI digest was corrected this way. Backfilled issues keep their badge and original snapshot link. Nothing is rewritten silently.
- Failed editorial tasks keep the last valid issue; re-runs don't duplicate issues or counts. PDFs are kept as standalone archives and are excluded from the parseable HTML statistics.
- Sources and third-party material: [数据来源.md](数据来源.md), [补档说明.md](补档说明.md), [NOTICE.md](NOTICE.md) (Chinese).

## License

Original code is released under the [MIT](LICENSE) license. Magazine content is generated from public GitHub data and public news sources; third-party projects, news, papers and archived material keep their own rights — see [NOTICE](NOTICE.md).
