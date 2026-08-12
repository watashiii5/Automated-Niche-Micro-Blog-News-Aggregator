#!/usr/bin/env python3
"""
Automated Niche Micro-Blog & News Aggregator
============================================

Fetches items from a niche RSS/Atom feed, uses the official Google GenAI
(Gemini) SDK to filter and rewrite them into short, SEO-optimized markdown
posts, then publishes them into /posts and regenerates index.json + feed.xml.

All configuration is done through environment variables (see README.md).

Run locally:
    pip install -r requirements.txt
    GEMINI_API_KEY=... python script.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import feedparser
from google import genai
from google.genai import types as genai_types

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def log(msg: str) -> None:
    print(f"[blog] {msg}", flush=True)


def log_warn(msg: str) -> None:
    print(f"[blog][warn] {msg}", flush=True)


def log_err(msg: str) -> None:
    print(f"[blog][error] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Configuration (env vars, see README.md)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
INDEX_PATH = BASE_DIR / "index.json"
FEED_PATH = BASE_DIR / "feed.xml"

SITE_NAME = os.getenv("SITE_NAME", "NichePulse")
SITE_URL = os.getenv(
    "SITE_URL",
    "https://watashiii5.github.io/Automated-Niche-Micro-Blog-News-Aggregator/",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FEED_URL = os.getenv("FEED_URL", "https://hnrss.org/frontpage")
TOPIC = os.getenv(
    "TOPIC",
    "AI tools and apps, open-source AI models, indie hacker launches, and emerging tech news",
)
USER_AGENT = os.getenv(
    "USER_AGENT",
    "NicheMicroBlogAggregator/1.0 (+https://github.com/watashiii5/Automated-Niche-Micro-Blog-News-Aggregator)",
)
MAX_FETCH = _env_int("MAX_FETCH", 15)
MAX_POSTS_PER_RUN = _env_int("MAX_POSTS_PER_RUN", 2)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
AUTH_PATH = BASE_DIR / "site_auth.json"
PBKDF2_ITERATIONS = _env_int("PBKDF2_ITERATIONS", 100_000)

PROMPT_TEMPLATE = """You are the editor of "{site}", a hyper-niche micro-blog that publishes short, punchy posts about: {topic}

SOURCE MATERIAL
---------------
Title: {title}
URL: {link}
Excerpt: {summary}

YOUR TASK
---------
1. Judge whether the source is genuinely relevant to the niche described above.
   If it is NOT relevant, respond with exactly: {"skip": true}
2. If it IS relevant, rewrite it into a fresh, engaging, SEO-optimized
   micro-blog post. Write ORIGINAL copy — never quote or copy sentences
   from the source.
3. Respond with STRICT JSON only (no markdown fences), shaped exactly like:
{
  "title": "punchy, keyword-rich title, under 90 characters, no quotes inside",
  "summary": "1-2 sentences, under 220 characters, hooks the reader",
  "tags": ["3-5 lowercase single-word tags"],
  "body": "Markdown body: 2-4 short paragraphs, under 250 words, no H1 heading. Use short sentences and one small bulleted list if useful. End with a single line linking to the source URL."
}

RULES
-----
- Only use facts present in the source. Never invent stats, quotes, or dates.
- Keep the tone upbeat, skimmable, and friendly.
- Return nothing except the JSON object.
"""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def clean_text(text: str) -> str:
    text = HTML_TAG_RE.sub(" ", text or "")
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def slugify(text: str, max_len: int = 64) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:max_len].strip("-") or "post"


# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------

def fetch_feed(url: str) -> feedparser.FeedParserDict:
    log(f"Fetching feed: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    headers = {"content-type": resp.headers.get("Content-Type") or "application/xml; charset=utf-8"}
    return feedparser.parse(raw, response_headers=headers)


# ---------------------------------------------------------------------------
# Gemini content generation
# ---------------------------------------------------------------------------

def generate_post(client: genai.Client, entry: dict) -> dict | None:
    title = clean_text(entry.get("title") or "Untitled")
    link = entry.get("link") or ""

    summary = entry.get("summary") or entry.get("description")
    if not summary and entry.get("content"):
        summary = entry["content"][0].get("value", "")
    summary = clean_text(summary)

    prompt = (
        PROMPT_TEMPLATE
        .replace("{site}", SITE_NAME)
        .replace("{topic}", TOPIC)
        .replace("{title}", title)
        .replace("{link}", link)
        .replace("{summary}", summary)
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8,
            ),
        )
    except Exception as exc:
        log_warn(f"Gemini call failed for '{title}': {exc}")
        return None

    raw = response.text or ""
    if not raw:
        log_warn(f"Empty Gemini response for '{title}'")
        return None

    cleaned = JSON_FENCE_RE.sub("", raw).strip()
    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                data = None

    if not isinstance(data, dict):
        log_warn(f"Could not parse Gemini output for '{title}'")
        return None

    if data.get("skip"):
        log(f"Skipped (filtered out): {title}")
        return None

    new_title = str(data.get("title") or title).strip()[:120] or title
    summary = clean_text(str(data.get("summary") or ""))[:400]
    body = str(data.get("body") or "").strip()

    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [re.sub(r"[^a-z0-9+#.-]", "-", str(t).strip().lower()) for t in tags if str(t).strip()]
    tags = tags[:6]

    if not body:
        body = f"**Source:** [{new_title}]({link})"
    if link and "http" not in body:
        body = body.rstrip() + f"\n\n**Source:** [{new_title}]({link})"

    return {
        "title": new_title,
        "summary": summary or body[:200],
        "tags": tags,
        "body": body,
        "source_url": link,
        "source_title": title,
    }


# ---------------------------------------------------------------------------
# Markdown files
# ---------------------------------------------------------------------------

def format_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for key in ("title", "date", "tags", "summary", "source_url", "source_title"):
        value = meta.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            items = ", ".join(json.dumps(t, ensure_ascii=False) for t in value)
            lines.append(f"{key}: [{items}]")
        else:
            value = str(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}: "{value}"')
    lines.append("---")
    return "\n".join(lines)


def save_post(post: dict) -> Path:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    base = slugify(post["title"])
    candidate = POSTS_DIR / f"{today}-{base}.md"
    counter = 1
    while candidate.exists():
        candidate = POSTS_DIR / f"{today}-{base}-{counter}.md"
        counter += 1

    meta = {
        "title": post["title"],
        "date": today,
        "tags": post["tags"],
        "summary": post["summary"],
        "source_url": post["source_url"],
        "source_title": post["source_title"],
    }
    content = format_frontmatter(meta) + "\n" + post["body"].strip() + "\n"
    candidate.write_text(content, encoding="utf-8")
    return candidate


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if key == "tags":
            try:
                meta[key] = json.loads(raw)
            except json.JSONDecodeError:
                meta[key] = [t.strip().strip("\"'") for t in raw.strip("[]").split(",") if t.strip()]
        else:
            meta[key] = raw.strip("\"'")
    return meta, text[match.end():]


def scan_posts() -> list[dict]:
    posts: list[dict] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta, _ = parse_frontmatter(text)
        if not meta.get("title") or not meta.get("date"):
            continue
        posts.append(
            {
                "title": meta["title"],
                "date": meta.get("date", ""),
                "tags": meta.get("tags", []),
                "summary": meta.get("summary", ""),
                "source_url": meta.get("source_url", ""),
                "source_title": meta.get("source_title", ""),
                "slug": path.stem,
                "file": f"posts/{path.name}",
            }
        )
    posts.sort(key=lambda p: (p["date"], p["title"].lower()), reverse=True)
    return posts


# ---------------------------------------------------------------------------
# index.json + feed.xml
# ---------------------------------------------------------------------------

def write_index(posts: list[dict]) -> None:
    payload = {
        "site": {"name": SITE_NAME, "url": SITE_URL},
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(posts),
        "posts": posts,
    }
    INDEX_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"index.json updated with {len(posts)} post(s)")


def write_feed(posts: list[dict]) -> None:
    ns = "http://www.w3.org/2005/Atom"
    feed = ET.Element(f"{{{ns}}}feed")
    ET.SubElement(feed, f"{{{ns}}}title").text = SITE_NAME
    ET.SubElement(feed, f"{{{ns}}}id").text = (SITE_URL or "urn:site").rstrip("/") + "/"
    ET.SubElement(feed, f"{{{ns}}}updated").text = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if SITE_URL:
        ET.SubElement(feed, f"{{{ns}}}link", {"rel": "self", "href": SITE_URL.rstrip("/") + "/feed.xml"})

    for post in posts:
        entry = ET.SubElement(feed, f"{{{ns}}}entry")
        ET.SubElement(entry, f"{{{ns}}}title").text = post["title"]
        ET.SubElement(entry, f"{{{ns}}}id").text = "urn:uuid:" + hashlib.md5(post["file"].encode("utf-8")).hexdigest()
        if post.get("source_url"):
            ET.SubElement(entry, f"{{{ns}}}link", {"rel": "alternate", "href": post["source_url"]})
        if post.get("summary"):
            ET.SubElement(entry, f"{{{ns}}}summary").text = post["summary"]
        ET.SubElement(entry, f"{{{ns}}}published").text = f"{post['date']}T00:00:00Z"
        ET.SubElement(entry, f"{{{ns}}}updated").text = f"{post['date']}T00:00:00Z"

    ET.indent(feed, space="  ")
    tree = ET.ElementTree(feed)
    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
    log(f"feed.xml updated with {len(posts)} entry(s)")


# ---------------------------------------------------------------------------
# Client-side login gate (site_auth.json)
# ---------------------------------------------------------------------------

def generate_auth_file(username: str, password: str, iterations: int = PBKDF2_ITERATIONS) -> Path:
    """Derive a salted PBKDF2 hash of the password and write site_auth.json.

    NOTE: This is a CLIENT-SIDE gate only. GitHub Pages has no server, so
    this cannot provide real access control — it only deters casual visitors.
    The plaintext credentials are never written to disk; they stay in GitHub
    secrets and only a salted hash lands in the deployed site.
    """
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations)
    payload = {
        "v": 1,
        "username_hash": hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest(),
        "salt": salt,
        "iterations": iterations,
        "password_hash": dk.hex(),
        "note": "Client-side gate only. This file is public on GitHub Pages and is not real security.",
    }
    AUTH_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {AUTH_PATH.name} (hashed credentials; plaintext stays in GitHub secrets)")
    return AUTH_PATH


def auth_cli() -> int:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        log_warn("ADMIN_USERNAME / ADMIN_PASSWORD secrets not set - login gate skipped, blog stays public.")
        return 0
    generate_auth_file(ADMIN_USERNAME, ADMIN_PASSWORD)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    log(f"Config: model={GEMINI_MODEL} feed={FEED_URL} max_fetch={MAX_FETCH} max_posts={MAX_POSTS_PER_RUN}")

    if not GEMINI_API_KEY:
        log_err("GEMINI_API_KEY environment variable is not set.")
        return 1

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        feed = fetch_feed(FEED_URL)
    except Exception as exc:
        log_err(f"Failed to fetch feed: {exc}")
        return 1

    if not feed.entries:
        log_warn("Feed returned no entries; nothing to do.")

    existing = {p["title"].lower() for p in scan_posts()}

    created = 0
    for entry in feed.entries[:MAX_FETCH]:
        if created >= MAX_POSTS_PER_RUN:
            break
        title = clean_text(entry.get("title") or "")
        if not title or title.lower() in existing:
            continue
        post = generate_post(client, entry)
        if post is None:
            continue
        path = save_post(post)
        existing.add(post["title"].lower())
        created += 1
        log(f"Created post: {path.relative_to(BASE_DIR)}")

    posts = scan_posts()
    write_index(posts)
    write_feed(posts)
    log(f"Done. {created} new post(s) generated, {len(posts)} total.")
    return 0


if __name__ == "__main__":
    if "--auth" in sys.argv:
        sys.exit(auth_cli())
    sys.exit(main())
