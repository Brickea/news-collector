#!/usr/bin/env python3
"""
news-collector: fetch RSS/Atom feeds, generate a dated markdown digest,
and (optionally) archive older digests.

Usage:
    python src/collector.py [path/to/config.yaml]

If no config path is given, defaults to config/config.yaml relative to the
directory from which the script is run.
"""

import html
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape HTML entities from *text*."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _truncate(text: str, max_chars: int = 300) -> str:
    """Return *text* truncated to *max_chars* characters, appending '…'."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    """Load and return the YAML configuration from *config_path*."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_rss(url: str, max_items: int = 10) -> list:
    """Parse an RSS/Atom feed at *url* and return up to *max_items* articles.

    Each article is a dict with keys: title, link, summary, published.
    """
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:max_items]:
        summary = _strip_html(entry.get("summary", ""))
        articles.append(
            {
                "title": _strip_html(entry.get("title", "No title")),
                "link": entry.get("link", ""),
                "summary": _truncate(summary),
                "published": entry.get("published", ""),
            }
        )
    return articles


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(date: datetime, news_by_source: dict) -> str:
    """Return a markdown string for the daily digest.

    *news_by_source* is an ordered dict mapping source name -> list of article
    dicts (title, link, summary, published).
    """
    lines = [
        f"# 📰 News Digest – {date.strftime('%Y-%m-%d')}",
        "",
        f"> Generated at {date.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "---",
        "",
    ]

    if not news_by_source:
        lines.append("*No articles were collected. Check your configuration.*")
        return "\n".join(lines)

    for source_name, articles in news_by_source.items():
        if not articles:
            continue
        lines.append(f"## {source_name}")
        lines.append("")
        for article in articles:
            title = article["title"] or "Untitled"
            link = article["link"]
            summary = article.get("summary", "")
            published = article.get("published", "")

            # Heading with hyperlink to original article
            if link:
                lines.append(f"### [{title}]({link})")
            else:
                lines.append(f"### {title}")

            if published:
                lines.append(f"*{published}*")
                lines.append("")

            if summary:
                lines.append(summary)
                lines.append("")

            if link:
                lines.append(f"🔗 [Read original]({link})")

            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Archiving
# ---------------------------------------------------------------------------

def archive_old_files(
    output_dir: Path,
    archive_dir: Path,
    today_filename: str,
    archive_format: str,
    run_date: datetime,
) -> None:
    """Move markdown files older than today from *output_dir* into *archive_dir*."""
    for filepath in sorted(output_dir.glob("*.md")):
        if filepath.name in (today_filename, "README.md"):
            continue
        dest_subdir = archive_dir / run_date.strftime(archive_format)
        dest_subdir.mkdir(parents=True, exist_ok=True)
        dest = dest_subdir / filepath.name
        filepath.rename(dest)
        print(f"  Archived: {filepath.name} → {dest}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_news(config_path: str = "config/config.yaml") -> Path:
    """Run the full collection pipeline and return the path to the output file."""
    config = load_config(config_path)

    enabled_categories: set = set(config.get("categories", []))
    sources: list = config.get("sources", [])
    output_cfg: dict = config.get("output", {})
    archive_cfg: dict = config.get("archive", {})

    output_dir = Path(output_cfg.get("dir", "docs"))
    archive_dir = Path(output_cfg.get("archive_dir", "docs/archive"))
    global_max_items: int = int(output_cfg.get("max_items_per_source", 10))

    now = datetime.now(tz=timezone.utc)

    # --- Fetch articles ---------------------------------------------------
    news_by_source: dict = {}

    for source in sources:
        if not source.get("enabled", True):
            continue

        source_categories: set = set(source.get("categories", []))

        # Skip source if none of its categories are in the enabled set
        if enabled_categories and source_categories and not source_categories & enabled_categories:
            continue

        name: str = source["name"]
        src_type: str = source.get("type", "rss")
        max_items: int = int(source.get("max_items", global_max_items))

        if src_type == "rss":
            try:
                print(f"  Fetching {name} …")
                articles = fetch_rss(source["url"], max_items)
                news_by_source[name] = articles
                print(f"    → {len(articles)} article(s)")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"  ⚠ Failed to fetch {name}: {exc}", file=sys.stderr)
        else:
            print(f"  ⚠ Unsupported source type '{src_type}' for {name}", file=sys.stderr)

    # --- Write markdown ---------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    today_filename = f"{now.strftime('%Y-%m-%d')}.md"
    output_file = output_dir / today_filename

    content = generate_markdown(now, news_by_source)
    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"\n✅ Digest written: {output_file}")

    # --- Archive ----------------------------------------------------------
    if archive_cfg.get("enabled", False):
        archive_format: str = archive_cfg.get("format", "%Y/%m")
        print("\nArchiving old digests …")
        archive_old_files(output_dir, archive_dir, today_filename, archive_format, now)

    return output_file


if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    collect_news(cfg)
