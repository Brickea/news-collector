#!/usr/bin/env python3
"""
Generate index.md with a list of all news digests for GitHub Pages.

This script scans the docs directory for all daily digest files and generates
an index.md file that lists them in reverse chronological order.
"""

import os
import re
from datetime import datetime
from pathlib import Path


def find_digest_files(docs_dir: Path) -> list[tuple[datetime, str]]:
    """Find all digest markdown files in docs directory.

    Returns:
        List of tuples (date, relative_path) sorted by date (newest first)
    """
    digests = []

    # Pattern for digest files: YYYY-MM-DD.md
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})\.md$')

    # Search in docs root directory
    for file in docs_dir.glob('*.md'):
        match = pattern.match(file.name)
        if match and file.name not in ['README.md', 'index.md']:
            date_str = match.group(1)
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                digests.append((date, file.name))
            except ValueError:
                continue

    # Search in archive directory
    archive_dir = docs_dir / 'archive'
    if archive_dir.exists():
        for md_file in archive_dir.rglob('*.md'):
            match = pattern.match(md_file.name)
            if match and md_file.name not in ['README.md', 'DEDUP_ALGORITHM.md']:
                date_str = match.group(1)
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    # Get relative path from docs directory
                    rel_path = md_file.relative_to(docs_dir)
                    digests.append((date, str(rel_path)))
                except ValueError:
                    continue

    # Sort by date, newest first
    digests.sort(reverse=True)
    return digests


def generate_index_content(digests: list[tuple[datetime, str]]) -> str:
    """Generate the index.md content with all digest links.

    Args:
        digests: List of (date, path) tuples sorted by date

    Returns:
        Full content of index.md as string
    """
    # Get recent digests (last 30 days)
    recent_digests = digests[:30]

    # Build recent digests section
    recent_section = []
    for i, (date, path) in enumerate(recent_digests):
        date_str = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A')

        # Create link with emoji indicator for latest
        emoji = "🌟" if i == 0 else "📰"
        label = "Latest digest" if i == 0 else day_name

        # Convert .md to .html for GitHub Pages
        html_path = path.replace('.md', '.html')
        recent_section.append(f"- [{emoji} {date_str}]({html_path}) - {label}")

    recent_digests_text = '\n'.join(recent_section)

    # Build archive by year/month
    archive_by_period = {}
    for date, path in digests:
        year = date.year
        month = date.strftime('%B')  # Full month name
        key = f"{year}-{date.month:02d}"
        display = f"{month} {year}"

        if key not in archive_by_period:
            archive_by_period[key] = {
                'display': display,
                'year': year,
                'month': date.month,
                'files': []
            }
        archive_by_period[key]['files'].append((date, path))

    # Sort archive periods (newest first)
    sorted_periods = sorted(archive_by_period.items(), reverse=True)

    # Build archive section
    archive_section = []
    for key, info in sorted_periods:
        year = info['year']
        month = info['month']
        count = len(info['files'])

        # Check if archive directory exists
        archive_path = f"archive/{year}/{month:02d}/"
        archive_section.append(f"- [{info['display']}]({archive_path}) - {count} digest{'s' if count > 1 else ''}")

    archive_list_text = '\n'.join(archive_section) if archive_section else "- No archived digests yet"

    # Get today's date for the latest digest link
    today = datetime.now().strftime('%Y-%m-%d')
    latest_digest_path = digests[0][1] if digests else f"{today}.md"
    # Convert .md to .html for GitHub Pages
    latest_digest_html = latest_digest_path.replace('.md', '.html')

    # Generate full index content
    content = f"""---
layout: default
title: 📰 Daily News Digest
---

# 📰 Daily News Digest

> Your daily curated news from around the world

Welcome to the **Daily News Digest**! This is an automated collection of the latest news articles from trusted sources across multiple categories including Technology & AI, Business & Finance, World News, Health, Science, and Coding & Development.

## 📅 Latest Digest

<div class="latest-digest" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin: 2rem 0; color: white;">
  <h3 style="margin-top: 0; color: white;">🌟 Today's News</h3>
  <p style="font-size: 1.2rem; margin-bottom: 1rem;">{today}</p>
  <a href="{latest_digest_html}" style="display: inline-block; background: white; color: #667eea; padding: 0.75rem 2rem; border-radius: 6px; text-decoration: none; font-weight: bold; transition: transform 0.2s;">
    📖 Read Today's Digest →
  </a>
</div>

## 🗂️ Archive

Browse through our collection of daily news digests:

### 📆 Recent Digests

<div class="archive-grid" style="display: grid; gap: 1rem; margin-top: 1.5rem;">

{recent_digests_text}

</div>

### 📚 Full Archive by Period

{archive_list_text}

## 📊 Categories

Our news digest covers the following categories:

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0;">
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
    <strong>🔬 Technology & AI</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Latest developments in tech and AI</p>
  </div>
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #764ba2;">
    <strong>💻 Coding & Development</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Programming news and trends</p>
  </div>
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #f093fb;">
    <strong>💼 Business & Finance</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Market updates and business news</p>
  </div>
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #4facfe;">
    <strong>🌍 World News</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Global events and headlines</p>
  </div>
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #43e97b;">
    <strong>🏥 Health</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Health and medical news</p>
  </div>
  <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #fa709a;">
    <strong>🔭 Science</strong>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">Scientific discoveries and research</p>
  </div>
</div>

## 🚀 Features

- **Automated Daily Updates** - Fresh news collected every day at 08:00 UTC
- **Multiple Trusted Sources** - Curated from BBC, Reuters, TechCrunch, NASA, and more
- **Organized Categories** - Easy navigation by topic
- **Chinese Translations** - AI-powered translations for non-Chinese content
- **Beautiful Cover Images** - NASA Astronomy Picture of the Day
- **Rich Markdown Format** - Clean, readable layout with visual separators

## 🔗 Links

- [GitHub Repository](https://github.com/Brickea/news-collector) - View the source code and configuration
- [Latest Digest]({latest_digest_html}) - Today's news
- [Archive](archive/) - Browse past digests

---

<div style="text-align: center; padding: 2rem 0; color: #666;">
  <p>📰 Powered by <a href="https://github.com/Brickea/news-collector">news-collector</a></p>
  <p style="font-size: 0.9rem;">Automatically updated daily via GitHub Actions</p>
  <p style="font-size: 0.8rem; margin-top: 0.5rem;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
"""

    return content


def generate_archive_index(digests: list[tuple[datetime, str]]) -> str:
    """Generate the main archive/index.md content.

    Args:
        digests: List of (date, path) tuples sorted by date

    Returns:
        Full content of archive/index.md as string
    """
    # Build archive by year/month
    archive_by_period = {}
    for date, path in digests:
        year = date.year
        month = date.strftime('%B')  # Full month name
        key = f"{year}-{date.month:02d}"
        display = f"{month} {year}"

        if key not in archive_by_period:
            archive_by_period[key] = {
                'display': display,
                'year': year,
                'month': date.month,
                'files': []
            }
        archive_by_period[key]['files'].append((date, path))

    # Sort archive periods (newest first)
    sorted_periods = sorted(archive_by_period.items(), reverse=True)

    # Build archive section
    archive_section = []
    for key, info in sorted_periods:
        year = info['year']
        month = info['month']
        count = len(info['files'])

        archive_path = f"{year}/{month:02d}/"
        archive_section.append(f"- [{info['display']}]({archive_path}) - {count} digest{'s' if count > 1 else ''}")

    archive_list_text = '\n'.join(archive_section) if archive_section else "- No archived digests yet"

    content = f"""---
layout: default
title: 📰 News Archive
---

# 📰 News Archive

> Browse all past news digests

[← Back to Home](../)

## 📚 Archive by Period

{archive_list_text}

---

<div style="text-align: center; padding: 2rem 0; color: #666;">
  <p>📰 Powered by <a href="https://github.com/Brickea/news-collector">news-collector</a></p>
</div>
"""

    return content


def generate_period_index(year: int, month: int, period_digests: list[tuple[datetime, str]], docs_dir: Path) -> str:
    """Generate archive/YYYY/MM/index.md content for a specific period.

    Args:
        year: Year number
        month: Month number (1-12)
        period_digests: List of (date, path) tuples for this period
        docs_dir: Base docs directory path

    Returns:
        Full content of period index.md as string
    """
    month_name = datetime(year, month, 1).strftime('%B')

    # Build digest list
    digest_section = []
    for date, path in period_digests:
        date_str = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A')

        # Calculate relative path from archive/YYYY/MM/ to the digest file
        # path is relative to docs_dir, e.g., "archive/2026/02/2026-02-23.md"
        digest_filename = Path(path).name.replace('.md', '.html')
        digest_section.append(f"- [{date_str}]({digest_filename}) - {day_name}")

    digest_list_text = '\n'.join(digest_section) if digest_section else "- No digests for this period"

    content = f"""---
layout: default
title: 📰 {month_name} {year} Archive
---

# 📰 {month_name} {year} Archive

> News digests from {month_name} {year}

[← Back to Archive](../../) | [← Back to Home](../../../)

## 📅 Digests

{digest_list_text}

---

<div style="text-align: center; padding: 2rem 0; color: #666;">
  <p>📰 Powered by <a href="https://github.com/Brickea/news-collector">news-collector</a></p>
</div>
"""

    return content


def main():
    """Main function to generate index.md."""
    # Get the repository root (parent of src directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent if script_dir.name == 'src' else script_dir
    docs_dir = repo_root / 'docs'

    if not docs_dir.exists():
        print(f"Error: docs directory not found at {docs_dir}")
        return 1

    # Find all digest files
    print(f"Scanning {docs_dir} for digest files...")
    digests = find_digest_files(docs_dir)
    print(f"Found {len(digests)} digest files")

    if not digests:
        print("Warning: No digest files found")
        return 1

    # Generate main index content
    print("Generating index.md...")
    content = generate_index_content(digests)

    # Write to index.md
    index_path = docs_dir / 'index.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Successfully generated {index_path}")

    # Generate archive/index.md
    print("Generating archive/index.md...")
    archive_dir = docs_dir / 'archive'
    archive_dir.mkdir(exist_ok=True)

    archive_content = generate_archive_index(digests)
    archive_index_path = archive_dir / 'index.md'
    with open(archive_index_path, 'w', encoding='utf-8') as f:
        f.write(archive_content)

    print(f"✅ Successfully generated {archive_index_path}")

    # Generate period-specific index files (archive/YYYY/MM/index.md)
    print("Generating period index files...")
    archive_by_period = {}
    for date, path in digests:
        year = date.year
        month = date.month
        key = f"{year}-{month:02d}"

        if key not in archive_by_period:
            archive_by_period[key] = {
                'year': year,
                'month': month,
                'files': []
            }
        archive_by_period[key]['files'].append((date, path))

    period_count = 0
    for key, info in archive_by_period.items():
        year = info['year']
        month = info['month']
        period_digests = sorted(info['files'], reverse=True)  # Sort by date, newest first

        # Create directory if needed
        period_dir = archive_dir / str(year) / f"{month:02d}"
        period_dir.mkdir(parents=True, exist_ok=True)

        # Generate and write period index
        period_content = generate_period_index(year, month, period_digests, docs_dir)
        period_index_path = period_dir / 'index.md'
        with open(period_index_path, 'w', encoding='utf-8') as f:
            f.write(period_content)

        print(f"  ✅ Generated {period_index_path}")
        period_count += 1

    print(f"✅ Successfully generated {period_count} period index files")
    print(f"   - Latest digest: {digests[0][0].strftime('%Y-%m-%d')}")
    print(f"   - Total digests: {len(digests)}")

    return 0


if __name__ == '__main__':
    exit(main())
