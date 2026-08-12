# NichePulse — Automated Niche Micro-Blog & News Aggregator

A zero-cost, fully automated micro-blog. A Python script fetches a niche tech/AI
RSS feed, uses the **Gemini API** (official `google-genai` SDK) to filter and
rewrite items into short, SEO-optimized markdown posts, commits them back to the
repo via **GitHub Actions** on a daily cron, and the whole thing is served for
free on **GitHub Pages**.

```
RSS / Atom feed ──► script.py ──► Gemini API (filter + rewrite) ──► /posts/*.md
                                 ──► index.json  (feed for the homepage)
                                 ──► feed.xml    (Atom RSS of your blog)
                                 ──► git commit + push (via GitHub Actions)
                                 ──► GitHub Pages serves index.html (Tailwind)
```

## Repository layout

```
.
├── .github/workflows/build_blog.yml  # daily cron + auto commit/push
├── posts/                            # generated markdown posts (frontmatter)
├── script.py                         # core content engine
├── requirements.txt                  # Python dependencies
├── index.html                        # frontend (Tailwind CDN, loads index.json)
├── index.json                        # generated post index (homepage feed)
├── feed.xml                          # generated Atom feed
├── .nojekyll                         # disables Jekyll so .md files stay raw
└── .gitignore
```

## Quick start (local test)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# Windows (PowerShell)
$env:GEMINI_API_KEY = "your-key"
python script.py

# macOS / Linux
# GEMINI_API_KEY=your-key python script.py
```

After the first run you'll see `posts/YYYY-MM-DD-<slug>.md`, `index.json`, and
`feed.xml`. Open `index.html` in a browser or serve it locally:

```bash
python -m http.server 8000
```

## Deploy to GitHub (5 minutes)

1. Create the repository
   [github.com/new](https://github.com/new) (e.g. `Automated-Niche-Micro-Blog-News-Aggregator`).
2. Push these files to the default branch (main).
3. Add your Gemini API key as a **repository secret**:
   `Settings → Secrets and variables → Actions → New repository secret`
   - Name: `GEMINI_API_KEY`
   - Value: get a free key at https://aistudio.google.com/apikey
4. Enable GitHub Pages:
   `Settings → Pages → Build and deployment → Source: Deploy from a branch`
   - Branch: `main`, folder: `/ (root)`, Save.
5. Go to the **Actions** tab and run the **Build Blog** workflow via
   *Run workflow* to trigger the first build immediately (no need to wait for
   the cron).

Your blog will then update itself daily at 06:00 UTC. 🎉

## How it works

1. **Fetch** — `script.py` pulls the latest entries from `FEED_URL` (default:
   Hacker News front page) using `feedparser` with a proper User-Agent.
2. **Filter & rewrite** — each candidate entry is sent to Gemini with a strict
   prompt: reject off-topic items (`{"skip": true}`) and rewrite the rest into
   original, SEO-optimized markdown with a title, 1-2 sentence summary, tags,
   and a short body. The model replies with structured JSON.
3. **Publish** — valid results are saved as `posts/YYYY-MM-DD-<slug>.md` with
   YAML-ish frontmatter (`title`, `date`, `tags`, `summary`, `source_url`,
   `source_title`). Duplicate titles are skipped.
4. **Index** — `index.json` and `feed.xml` are regenerated from every post in
   `/posts` (sorted newest-first) and committed back to the repo.
5. **Serve** — `index.html` fetches `index.json`, renders a dark, minimal
   Tailwind card list with live search + tag filters, and renders the full
   markdown of each post on click (via `marked` + `DOMPurify`).

### Example generated post (`posts/2026-08-12-example.md`)

```markdown
---
title: "Open-Source Model Surpasses Frontier Benchmarks"
date: "2026-08-12"
tags: ["ai", "opensource", "llm"]
summary: "A new open-weight model is giving closed labs a run for their money."
source_url: "https://example.com/story"
source_title: "Original story headline"
---

Short, punchy rewrite of the original story... (written by Gemini)

> Source: [Open-Source Model Surpasses Frontier Benchmarks](https://example.com/story)
```

## Configuration

Everything is configurable via environment variables (set them in the workflow,
or inline locally).

| Variable             | Default                                  | Description                                        |
| -------------------- | ---------------------------------------- | -------------------------------------------------- |
| `GEMINI_API_KEY`     | *(required)*                             | Google AI Studio API key.                          |
| `GEMINI_MODEL`       | `gemini-2.5-flash`                       | Gemini model to use for generation.                |
| `FEED_URL`           | `https://hnrss.org/frontpage`            | RSS/Atom feed to aggregate.                        |
| `TOPIC`              | `AI tools..., indie hacker launches...`  | Niche description used for relevance filtering.    |
| `MAX_FETCH`          | `15`                                     | How many feed entries to consider per run.         |
| `MAX_POSTS_PER_RUN`  | `2`                                      | Max posts to publish per run.                      |
| `SITE_NAME`          | `NichePulse`                             | Used in the feed + JSON index.                     |
| `SITE_URL`           | your Pages URL                           | Used for the `feed.xml` self link.                 |

### Picking your niche feed

Swap `FEED_URL` to target any niche you like:

- **Hacker News AI search:** `https://hnrss.org/newest?q=ai+llm`
- **arXiv AI papers:** `http://export.arxiv.org/rss/cs.AI`
- **Hugging Face blog:** `https://huggingface.co/blog/feed.xml`
- **Reddit r/MachineLearning:** `https://www.reddit.com/r/MachineLearning/new/.rss`
- **GitHub trending (via RSSHub):** `https://rsshub.app/github/trending/daily/ai`
- **Google AI blog:** `https://blog.google/technology/ai/rss/`

Tip: pair a niche feed with a matching `TOPIC` (e.g. `open-source diffusion
models`) so Gemini filters out anything off-message.

### Changing the schedule

Edit the `cron` line in `.github/workflows/build_blog.yml`:

```yaml
- cron: "0 6 * * *"   # minute hour day month weekday  → daily 06:00 UTC
```

## Important notes

- **GitHub disables cron workflows after 60 days of repo inactivity.**
  Any push re-enables them; you can also run the workflow manually via
  `workflow_dispatch`.
- The workflow uses the built-in `GITHUB_TOKEN`. If your repo has strict branch
  protection, create a `PAT` secret and push with it instead.
- Scheduled runs still regenerate `index.json`/`feed.xml` (fresh timestamps),
  so a commit happens even on days with no new posts — this keeps the site
  "last generated" marker current.
- Free GitHub Pages limits: ~100 builds/hour and 1 GB site size — plenty here.
- `index.html` is a static template; the posts themselves come from
  `index.json`, so there's nothing to rebuild after each run.

## Troubleshooting

| Problem                          | Fix                                                                 |
| -------------------------------- | ------------------------------------------------------------------- |
| `GEMINI_API_KEY is not set`      | Add the secret in `Settings → Secrets`, or set it locally.          |
| `Failed to fetch feed`           | Check `FEED_URL`; some feeds rate-limit. Try a different one above. |
| No posts generated               | Feed may have nothing new (dedupe by title) or Gemini skipped all.  |
| Pages shows raw text / 404       | Enable Pages on branch `main` at root, and keep `.nojekyll`.        |
| JSON is not valid / parse error  | Rare Gemini output is recovered heuristically; post is skipped.     |

## License

MIT — use it, remix it, make it yours.
