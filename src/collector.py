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
from urllib import request
import json

import feedparser
import yaml
from googletrans import Translator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_daily_cover_image(date: datetime) -> tuple[str, str, str]:
    """Get a daily cover image URL, attribution, and description.

    Tries multiple sources in order:
    1. NASA APOD (Astronomy Picture of the Day) - free, daily changing, high quality
    2. Picsum Photos - fallback with date-based seed for consistency

    Returns:
        tuple: (image_url, attribution_text, description)
    """
    date_str = date.strftime('%Y-%m-%d')

    # Try NASA APOD API (free, no key required for reasonable use)
    # This provides a different high-quality image every day
    try:
        # NASA APOD API - get picture for today
        apod_url = f"https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY&date={date_str}"

        with request.urlopen(apod_url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())

                # Check if it's an image (not a video)
                if data.get('media_type') == 'image':
                    img_url = data.get('url', '')
                    title = data.get('title', 'NASA APOD')
                    explanation = data.get('explanation', '')
                    attribution = f"*Image: {title} - NASA Astronomy Picture of the Day*"
                    # Truncate explanation to reasonable length for cover section
                    description = _truncate(explanation, max_chars=400) if explanation else ""
                    return img_url, attribution, description
    except Exception:
        # If NASA APOD fails, continue to fallback
        pass

    # Fallback: Use Picsum Photos with date-based seed for consistency
    # This ensures the same image appears for the same date
    date_seed = int(date.strftime('%Y%m%d')) % 1000  # Use modulo to get valid image ID
    picsum_url = f"https://picsum.photos/seed/{date_str}/1200/400"
    attribution = "*Image: Daily photo from Picsum Photos*"
    description = "A beautiful random photograph to brighten your day while you catch up on the latest news."

    return picsum_url, attribution, description


def _is_chinese(text: str) -> bool:
    """Check if text contains significant Chinese characters."""
    if not text:
        return False
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    return chinese_chars > len(text) * 0.3  # More than 30% Chinese characters


def _translate_to_chinese(text: str, translator: Translator) -> str:
    """Translate text to Chinese (simplified). Returns empty string on error."""
    if not text or _is_chinese(text):
        return ""
    try:
        result = translator.translate(text, dest='zh-cn')
        return result.text if result else ""
    except Exception:
        return ""


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


def _generate_shingles(text: str, k: int = 3) -> set:
    """Generate k-shingles (k-grams) from text for better similarity detection.

    Shingles capture word order and context better than simple word sets.
    For example, "machine learning" vs "learning machine" will have different shingles.

    Args:
        text: Input text
        k: Number of consecutive words in each shingle (default 3)

    Returns:
        Set of k-shingles
    """
    words = text.lower().split()
    if len(words) < k:
        # If text is too short, use the whole text as a single shingle
        return {' '.join(words)} if words else set()

    # Generate sliding window of k consecutive words
    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = ' '.join(words[i:i + k])
        shingles.add(shingle)
    return shingles


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using improved Jaccard similarity with shingles.

    相似度计算方法说明：
    1. **Shingle (k-gram) 方法**: 使用3个连续单词作为一个"瓦片"，相比单纯的词集合更能捕捉词序和上下文
       - 例如："machine learning model" 会生成 ["machine learning", "learning model"]
       - 这样 "machine learning" 和 "learning machine" 会被识别为不同

    2. **Jaccard 相似度**: similarity = |A ∩ B| / |A ∪ B|
       - 交集大小除以并集大小
       - 值域 [0, 1]，0表示完全不同，1表示完全相同
       - 科学性：这是信息检索领域的标准方法，适用于文本去重

    3. **优化**:
       - 使用集合运算 (set operations) 提高计算效率
       - 预计算shingles避免重复处理
       - 时间复杂度: O(n) where n is text length

    Returns:
        Similarity score between 0 (completely different) and 1 (identical).
    """
    if not text1 or not text2:
        # Two empty strings are considered identical
        if not text1 and not text2:
            return 1.0
        return 0.0

    # Generate shingles for both texts
    shingles1 = _generate_shingles(text1)
    shingles2 = _generate_shingles(text2)

    # Handle edge cases
    if not shingles1 and not shingles2:
        return 1.0
    if not shingles1 or not shingles2:
        return 0.0

    # Calculate Jaccard similarity
    intersection = shingles1 & shingles2
    union = shingles1 | shingles2

    return len(intersection) / len(union) if union else 0.0


def _deduplicate_articles(articles_by_source: dict, similarity_threshold: float = 0.7) -> dict:
    """Remove duplicate articles based on title and summary similarity.

    性能优化说明：
    1. **预计算shingles**: 避免重复计算相同文本的shingles
    2. **快速过滤**: 使用文本长度和关键词快速排除明显不同的文章
    3. **时间复杂度**: O(n²) 最坏情况，但通过快速过滤实际上接近 O(n·m)
       其中 n 是文章数，m 是平均相似文章数（通常 m << n）

    进一步优化建议（未实现，以保持代码简洁）：
    - LSH (Locality Sensitive Hashing): 可降至 O(n)，但需要额外依赖
    - MinHash: 可以近似计算Jaccard相似度，更快但有误差
    - 聚类方法: 先聚类再去重，适合大规模数据

    Args:
        articles_by_source: Dict mapping source name to dict with 'articles' and 'categories'
        similarity_threshold: Threshold above which articles are considered duplicates (0-1)

    Returns:
        Deduplicated articles_by_source with the same structure
    """
    # Collect all articles with their source info and precompute features
    all_articles = []
    for source_name, source_data in articles_by_source.items():
        for article in source_data.get('articles', []):
            combined_text = f"{article.get('title', '')} {article.get('summary', '')}"
            all_articles.append({
                'source': source_name,
                'categories': source_data.get('categories', []),
                'article': article,
                'combined_text': combined_text,
                'text_len': len(combined_text),  # Pre-compute for fast filtering
                'shingles': _generate_shingles(combined_text),  # Pre-compute shingles
            })

    # Deduplicate using optimized comparison
    seen = []
    deduplicated = []

    for item in all_articles:
        is_duplicate = False

        for seen_item in seen:
            # Fast filter: skip if text length differs significantly (>50%)
            # 快速过滤：如果文本长度差异超过50%，直接跳过
            len_ratio = min(item['text_len'], seen_item['text_len']) / max(item['text_len'], seen_item['text_len']) if max(item['text_len'], seen_item['text_len']) > 0 else 1
            if len_ratio < 0.5:
                continue

            # Calculate similarity using pre-computed shingles
            # 使用预计算的shingles提高性能
            if not item['shingles'] or not seen_item['shingles']:
                similarity = 0.0
            else:
                intersection = item['shingles'] & seen_item['shingles']
                union = item['shingles'] | seen_item['shingles']
                similarity = len(intersection) / len(union) if union else 0.0

            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            deduplicated.append(item)
            seen.append(item)

    # Reconstruct the articles_by_source structure
    result = {}
    for item in deduplicated:
        source = item['source']
        if source not in result:
            result[source] = {
                'articles': [],
                'categories': item['categories']
            }
        result[source]['articles'].append(item['article'])

    return result


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

def generate_markdown(date: datetime, news_by_source: dict, translator: Translator = None) -> str:
    """Return a markdown string for the daily digest.

    *news_by_source* is an ordered dict mapping source name -> dict with 'articles'
    and 'categories' keys.
    """
    # Add Jekyll front matter for GitHub Pages rendering
    lines = [
        "---",
        "layout: default",
        f"title: 📰 Daily News Digest · {date.strftime('%Y-%m-%d')}",
        "---",
        "",
        '<div style="margin-bottom: 1rem;">',
        '  <a href="/" style="display: inline-block; padding: 0.5rem 1rem; background: #667eea; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem;">← Back to Home</a>',
        '</div>',
        "",
        f"# 📰 Daily News Digest · {date.strftime('%Y-%m-%d')}",
        "",
        f"> 🗓️ Generated on {date.strftime('%Y-%m-%d')} at {date.strftime('%H:%M')} UTC",
        "",
    ]

    if not news_by_source:
        lines.append("---")
        lines.append("")
        lines.append("*No articles were collected. Check your configuration.*")
        return "\n".join(lines)

    # Add cover section with daily changing image
    # Get daily cover image from NASA APOD or Picsum fallback
    cover_url, cover_attribution, cover_description = _get_daily_cover_image(date)

    lines.extend([
        "## 📸 Cover",
        "",
        f"![Daily News]({cover_url})",
        "",
        cover_attribution,
        "",
    ])

    # Add description if available
    if cover_description:
        lines.extend([
            f"> {cover_description}",
            "",
        ])

    lines.extend([
        "*Stay informed with today's curated news from around the world.*",
        "",
    ])

    # Organize by categories
    categories_map = {
        'technology': '🔬 Technology & AI',
        'business': '💼 Business & Finance',
        'world': '🌍 World News',
        'health': '🏥 Health',
        'science': '🔭 Science',
        'coding': '💻 Coding & Development'
    }

    # Group sources by their primary category
    news_by_category = {}
    for source_name, source_data in news_by_source.items():
        articles = source_data.get('articles', [])
        categories = source_data.get('categories', [])
        if not articles:
            continue

        # Use the first category as primary
        primary_cat = categories[0] if categories else 'other'
        if primary_cat not in news_by_category:
            news_by_category[primary_cat] = []
        news_by_category[primary_cat].append((source_name, articles))

    # Add table of contents
    if news_by_category:
        lines.extend([
            "## 📑 Table of Contents",
            "",
        ])
        for category in ['technology', 'coding', 'business', 'world', 'health', 'science', 'other']:
            if category in news_by_category:
                category_title = categories_map.get(category, f'📑 {category.title()}')
                # Create anchor link
                anchor = category_title.lower().replace(' ', '-').replace('&', '').replace('🔬', '').replace('💼', '').replace('🌍', '').replace('🏥', '').replace('🔭', '').replace('💻', '').replace('📑', '').strip()
                lines.append(f"- [{category_title}](#{anchor})")
        lines.extend(["", "---", ""])

    # Render by category
    for category in ['technology', 'coding', 'business', 'world', 'health', 'science', 'other']:
        if category not in news_by_category:
            continue

        category_title = categories_map.get(category, f'📑 {category.title()}')
        lines.append(f"## {category_title}")
        lines.append("")

        for source_name, articles in news_by_category[category]:
            lines.append(f"### 📰 {source_name}")
            lines.append("")

            for idx, article in enumerate(articles, 1):
                title = article["title"] or "Untitled"
                link = article["link"]
                summary = article.get("summary", "")
                published = article.get("published", "")

                # Article card with better formatting
                lines.append(f"#### {idx}. {title}")
                lines.append("")

                if published:
                    lines.append(f"🕒 *Published: {published}*")
                    lines.append("")

                if summary:
                    # Add a quoted summary for better visual separation
                    lines.append(f"> {summary}")
                    lines.append("")

                    # Add Chinese translation if not already Chinese
                    if translator and not _is_chinese(title + summary):
                        title_zh = _translate_to_chinese(title, translator)
                        summary_zh = _translate_to_chinese(summary, translator)
                        if title_zh or summary_zh:
                            lines.append("**📖 中文翻译:**")
                            lines.append("")
                            if title_zh:
                                lines.append(f"**{title_zh}**")
                                lines.append("")
                            if summary_zh:
                                lines.append(summary_zh)
                            lines.append("")

                if link:
                    lines.append(f"🔗 **<a href=\"{link}\" target=\"_blank\">Read Full Article →</a>**")
                    lines.append("")

                # Visual separator between articles
                if idx < len(articles):
                    lines.append("---")
                    lines.append("")

            lines.append("")

        # Category separator
        lines.append("")
        lines.append("---")
        lines.append("")

    # Add footer
    lines.extend([
        "## 📌 About This Digest",
        "",
        "This daily news digest is automatically generated from various RSS feeds.",
        "",
        "- 🤖 Powered by automated collection and AI translation",
        "- 🌐 Sources from trusted news outlets worldwide",
        "- 📅 Published daily with the latest updates",
        "",
        f"*Last updated: {date.strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
    ])

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

def collect_news(
    config_path: str = "config/config.yaml",
    categories_override: list | None = None,
) -> Path:
    """Run the full collection pipeline and return the path to the output file.

    *categories_override* – when provided, replaces the ``categories`` list from
    the config file so the caller can choose which topics to collect without
    editing the YAML (e.g. when triggering manually via GitHub Actions).
    """
    config = load_config(config_path)

    if categories_override is not None:
        enabled_categories: set = set(categories_override)
    else:
        enabled_categories: set = set(config.get("categories", []))
    sources: list = config.get("sources", [])
    output_cfg: dict = config.get("output", {})
    archive_cfg: dict = config.get("archive", {})

    output_dir = Path(output_cfg.get("dir", "docs"))
    archive_dir = Path(output_cfg.get("archive_dir", "docs/archive"))
    global_max_items: int = int(output_cfg.get("max_items_per_source", 10))

    now = datetime.now(tz=timezone.utc)

    # Initialize translator
    translator = Translator()

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
                # Store articles along with category information
                news_by_source[name] = {
                    'articles': articles,
                    'categories': list(source_categories)
                }
                print(f"    → {len(articles)} article(s)")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"  ⚠ Failed to fetch {name}: {exc}", file=sys.stderr)
        else:
            print(f"  ⚠ Unsupported source type '{src_type}' for {name}", file=sys.stderr)

    # --- Deduplicate news -------------------------------------------------
    print("\nDeduplicating articles …")
    original_count = sum(len(data['articles']) for data in news_by_source.values())
    news_by_source = _deduplicate_articles(news_by_source, similarity_threshold=0.7)
    final_count = sum(len(data['articles']) for data in news_by_source.values())
    print(f"  → Removed {original_count - final_count} duplicate(s), {final_count} unique articles")

    # --- Write markdown ---------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    today_filename = f"{now.strftime('%Y-%m-%d')}.md"
    output_file = output_dir / today_filename

    content = generate_markdown(now, news_by_source, translator)
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect news and generate a dated Markdown digest."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/config.yaml",
        help="Path to the YAML config file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--categories",
        metavar="CAT1,CAT2",
        default=None,
        help=(
            "Comma-separated list of categories to collect, overriding the "
            "'categories' field in the config file "
            "(e.g. --categories technology,world)"
        ),
    )
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()] if args.categories else None
    collect_news(args.config, categories_override=cats)
