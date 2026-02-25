#!/usr/bin/env python3
"""
Generate summaries for daily news digests.

This script scans daily digest markdown files and creates summaries
that aggregate key information from the news articles collected.

Usage:
    python src/generate_summary.py
"""

import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def parse_digest_file(file_path: Path) -> dict:
    """Parse a digest markdown file to extract key information.

    Args:
        file_path: Path to the digest markdown file

    Returns:
        Dictionary with parsed information including:
        - date: Date of the digest
        - categories: Categories covered
        - sources: List of sources
        - article_count: Total number of articles
        - articles_by_category: Articles organized by category
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract date from filename
    filename = file_path.name
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})\.md', filename)
    if not date_match:
        return None

    date_str = date_match.group(1)
    date = datetime.strptime(date_str, '%Y-%m-%d')

    # Extract categories and articles
    categories = {}
    current_category = None
    current_source = None
    article_count = 0

    # Parse content line by line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Match category headers (e.g., "## 🔬 Technology & AI {#technology-ai}")
        category_match = re.match(r'^##\s+(.+?)\s+\{#.+\}', line)
        if category_match:
            current_category = category_match.group(1).strip()
            if current_category not in ['📸 Cover', '📑 Table of Contents', '📌 About This Digest']:
                categories[current_category] = {
                    'sources': [],
                    'articles': []
                }
            continue

        # Match source headers (e.g., "### 📰 TechCrunch {#techcrunch}")
        source_match = re.match(r'^###\s+📰\s+(.+?)\s+\{#.+\}', line)
        if source_match and current_category and current_category in categories:
            current_source = source_match.group(1).strip()
            if current_source not in categories[current_category]['sources']:
                categories[current_category]['sources'].append(current_source)
            continue

        # Match article headers (e.g., "#### 1. Article Title")
        article_match = re.match(r'^####\s+\d+\.\s+(.+)', line)
        if article_match and current_category and current_category in categories:
            article_title = article_match.group(1).strip()

            # Try to find the summary (quoted text on next few lines)
            summary = ""
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].startswith('> '):
                    summary = lines[j][2:].strip()
                    break

            categories[current_category]['articles'].append({
                'title': article_title,
                'summary': summary,
                'source': current_source
            })
            article_count += 1

    return {
        'date': date,
        'date_str': date_str,
        'categories': categories,
        'article_count': article_count,
        'file_path': file_path
    }


def generate_digest_summary(digest_info: dict) -> str:
    """Generate a text summary for a single digest.

    Args:
        digest_info: Parsed digest information

    Returns:
        Summary text
    """
    if not digest_info:
        return ""

    lines = []
    date_str = digest_info['date_str']
    categories = digest_info['categories']
    article_count = digest_info['article_count']

    # Summary header
    lines.append(f"**{date_str}** - {article_count} articles")

    # Category breakdown
    for category, data in categories.items():
        sources = data['sources']
        articles = data['articles']
        if articles:
            lines.append(f"  - {category}: {len(articles)} articles from {', '.join(sources[:3])}")

    return '\n'.join(lines)


def generate_period_summary(period_digests: list[dict], year: int, month: int) -> str:
    """Generate a summary for a specific period (month).

    Args:
        period_digests: List of digest information for the period
        year: Year
        month: Month (1-12)

    Returns:
        Summary markdown content
    """
    month_name = datetime(year, month, 1).strftime('%B')

    # Aggregate statistics
    total_articles = sum(d['article_count'] for d in period_digests)
    total_days = len(period_digests)

    # Category statistics
    category_stats = defaultdict(lambda: {'articles': 0, 'sources': set()})

    for digest in period_digests:
        for category, data in digest['categories'].items():
            category_stats[category]['articles'] += len(data['articles'])
            category_stats[category]['sources'].update(data['sources'])

    # Top categories
    sorted_categories = sorted(
        category_stats.items(),
        key=lambda x: x[1]['articles'],
        reverse=True
    )

    # Build summary content
    lines = [
        "---",
        "layout: default",
        f"title: 📊 {month_name} {year} Summary",
        "---",
        "",
        f"# 📊 {month_name} {year} Summary",
        "",
        f"> News digest summary for {month_name} {year}",
        "",
        f"[← Back to Summaries](../../../summaries/) | [← Back to Archive](../../) | [← Back to Home](../../../)",
        "",
        "## 📈 Overview",
        "",
        f"- **Total Days**: {total_days}",
        f"- **Total Articles**: {total_articles}",
        f"- **Average Articles per Day**: {total_articles // total_days if total_days > 0 else 0}",
        "",
        "## 📊 Category Breakdown",
        "",
    ]

    for category, stats in sorted_categories[:10]:  # Top 10 categories
        sources_list = ', '.join(sorted(list(stats['sources']))[:5])
        lines.append(f"### {category}")
        lines.append("")
        lines.append(f"- **Articles**: {stats['articles']}")
        lines.append(f"- **Sources**: {sources_list}")
        lines.append("")

    lines.extend([
        "## 📅 Daily Summaries",
        "",
    ])

    # Sort by date
    sorted_digests = sorted(period_digests, key=lambda d: d['date'])

    for digest in sorted_digests:
        date_str = digest['date_str']
        day_name = digest['date'].strftime('%A')
        article_count = digest['article_count']

        # Link to the actual digest
        digest_path = digest['file_path'].name.replace('.md', '.html')
        lines.append(f"### [{date_str}](../{digest_path}) - {day_name}")
        lines.append("")
        lines.append(f"**{article_count} articles** collected from:")
        lines.append("")

        for category, data in digest['categories'].items():
            if data['articles']:
                lines.append(f"- {category}: {len(data['articles'])} articles")

        lines.append("")

    lines.extend([
        "---",
        "",
        '<div style="text-align: center; padding: 2rem 0; color: #666;">',
        '  <p>📊 Summary generated by <a href="https://github.com/Brickea/news-collector">news-collector</a></p>',
        '</div>',
    ])

    return '\n'.join(lines)


def generate_summary_index(all_summaries: list[tuple[int, int, int]]) -> str:
    """Generate the main summaries index page.

    Args:
        all_summaries: List of (year, month, count) tuples

    Returns:
        Summary index markdown content
    """
    # Sort by year/month descending
    sorted_summaries = sorted(all_summaries, key=lambda x: (x[0], x[1]), reverse=True)

    lines = [
        "---",
        "layout: default",
        "title: 📊 News Summaries",
        "---",
        "",
        "# 📊 News Summaries",
        "",
        "> Monthly summaries of news digests",
        "",
        "[← Back to Home](../../)",
        "",
        "## 📅 Available Summaries",
        "",
    ]

    for year, month, count in sorted_summaries:
        month_name = datetime(year, month, 1).strftime('%B')
        summary_path = f"../../{year}/{month:02d}/summary.html"
        lines.append(f"- [{month_name} {year}]({summary_path}) - {count} digests")

    lines.extend([
        "",
        "---",
        "",
        '<div style="text-align: center; padding: 2rem 0; color: #666;">',
        '  <p>📊 Summaries generated by <a href="https://github.com/Brickea/news-collector">news-collector</a></p>',
        '</div>',
    ])

    return '\n'.join(lines)


def main():
    """Main function to generate summaries."""
    # Get repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent if script_dir.name == 'src' else script_dir
    docs_dir = repo_root / 'docs'

    if not docs_dir.exists():
        print(f"Error: docs directory not found at {docs_dir}")
        return 1

    # Find all digest files
    print("Scanning for digest files...")
    digest_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}\.md$')

    all_digests = []

    # Scan docs root
    for file in docs_dir.glob('*.md'):
        if digest_pattern.match(file.name):
            digest_info = parse_digest_file(file)
            if digest_info:
                all_digests.append(digest_info)

    # Scan archive
    archive_dir = docs_dir / 'archive'
    if archive_dir.exists():
        for md_file in archive_dir.rglob('*.md'):
            if digest_pattern.match(md_file.name):
                digest_info = parse_digest_file(md_file)
                if digest_info:
                    all_digests.append(digest_info)

    print(f"Found {len(all_digests)} digest files")

    if not all_digests:
        print("No digest files found")
        return 1

    # Group by year/month
    digests_by_period = defaultdict(list)
    for digest in all_digests:
        year = digest['date'].year
        month = digest['date'].month
        key = (year, month)
        digests_by_period[key].append(digest)

    # Create summaries directory structure
    summaries_dir = archive_dir / 'summaries'
    summaries_dir.mkdir(exist_ok=True)

    # Generate summaries for each period
    print("\nGenerating period summaries...")
    all_summaries = []

    for (year, month), period_digests in digests_by_period.items():
        # Create period directory in archive (not in summaries)
        period_dir = archive_dir / str(year) / f"{month:02d}"
        period_dir.mkdir(parents=True, exist_ok=True)

        # Generate summary
        summary_content = generate_period_summary(period_digests, year, month)
        summary_path = period_dir / 'summary.md'

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        print(f"  ✅ Generated summary for {year}-{month:02d} ({len(period_digests)} digests)")
        all_summaries.append((year, month, len(period_digests)))

    # Generate main summaries index
    print("\nGenerating summaries index...")
    summaries_index_content = generate_summary_index(all_summaries)
    summaries_index_path = summaries_dir / 'index.md'

    with open(summaries_index_path, 'w', encoding='utf-8') as f:
        f.write(summaries_index_content)

    print(f"✅ Successfully generated {summaries_index_path}")
    print(f"   - Total periods: {len(all_summaries)}")
    print(f"   - Total digests: {len(all_digests)}")

    return 0


if __name__ == '__main__':
    exit(main())
