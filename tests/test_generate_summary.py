"""
Tests for src/generate_summary.py

Run with:  pytest tests/
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Make the src package importable without an install step
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from generate_summary import (  # noqa: E402
    parse_digest_file,
    generate_digest_summary,
    generate_period_summary,
    generate_summary_index,
)


# ---------------------------------------------------------------------------
# Test parse_digest_file
# ---------------------------------------------------------------------------

class TestParseDigestFile:
    def test_parses_valid_digest(self, tmp_path):
        """Test parsing a valid digest file."""
        digest_content = """---
layout: default
title: 📰 Daily News Digest · 2026-02-24
---

# 📰 Daily News Digest · 2026-02-24

## 📸 Cover

![Daily News](https://example.com/image.jpg)

## 📑 Table of Contents

- [🔬 Technology & AI](#technology-ai)
  - [TechCrunch](#techcrunch)

---

## 🔬 Technology & AI {#technology-ai}

### 📰 TechCrunch {#techcrunch}

#### 1. Test Article Title

🕒 *Published: Mon, 24 Feb 2026 10:00:00 GMT*

> This is a test summary for the article.

🔗 **<a href="https://example.com/article" target="_blank">Read Full Article →</a>**

---

#### 2. Another Article

> Another summary here.

🔗 **<a href="https://example.com/article2" target="_blank">Read Full Article →</a>**

"""
        digest_file = tmp_path / "2026-02-24.md"
        digest_file.write_text(digest_content, encoding='utf-8')

        result = parse_digest_file(digest_file)

        assert result is not None
        assert result['date_str'] == '2026-02-24'
        assert result['article_count'] == 2
        assert '🔬 Technology & AI' in result['categories']
        assert 'TechCrunch' in result['categories']['🔬 Technology & AI']['sources']
        assert len(result['categories']['🔬 Technology & AI']['articles']) == 2

    def test_parses_multiple_categories(self, tmp_path):
        """Test parsing digest with multiple categories."""
        digest_content = """---
layout: default
title: 📰 Daily News Digest · 2026-02-24
---

# 📰 Daily News Digest · 2026-02-24

## 🔬 Technology & AI {#technology-ai}

### 📰 TechCrunch {#techcrunch}

#### 1. Tech Article

> Tech summary.

## 💼 Business & Finance {#business-finance}

### 📰 Financial Times {#financial-times}

#### 1. Business Article

> Business summary.

"""
        digest_file = tmp_path / "2026-02-24.md"
        digest_file.write_text(digest_content, encoding='utf-8')

        result = parse_digest_file(digest_file)

        assert result is not None
        assert len(result['categories']) == 2
        assert '🔬 Technology & AI' in result['categories']
        assert '💼 Business & Finance' in result['categories']

    def test_invalid_filename_returns_none(self, tmp_path):
        """Test that invalid filename returns None."""
        digest_file = tmp_path / "invalid-name.md"
        digest_file.write_text("content", encoding='utf-8')

        result = parse_digest_file(digest_file)
        assert result is None

    def test_empty_digest(self, tmp_path):
        """Test parsing digest with no articles."""
        digest_content = """---
layout: default
title: 📰 Daily News Digest · 2026-02-24
---

# 📰 Daily News Digest · 2026-02-24

---
"""
        digest_file = tmp_path / "2026-02-24.md"
        digest_file.write_text(digest_content, encoding='utf-8')

        result = parse_digest_file(digest_file)

        assert result is not None
        assert result['article_count'] == 0
        assert len(result['categories']) == 0


# ---------------------------------------------------------------------------
# Test generate_digest_summary
# ---------------------------------------------------------------------------

class TestGenerateDigestSummary:
    def test_generates_basic_summary(self):
        """Test generating a basic summary."""
        digest_info = {
            'date_str': '2026-02-24',
            'article_count': 5,
            'categories': {
                '🔬 Technology & AI': {
                    'sources': ['TechCrunch', 'The Verge'],
                    'articles': [
                        {'title': 'Article 1', 'summary': 'Summary 1', 'source': 'TechCrunch'},
                        {'title': 'Article 2', 'summary': 'Summary 2', 'source': 'The Verge'},
                    ]
                }
            }
        }

        summary = generate_digest_summary(digest_info)

        assert '2026-02-24' in summary
        assert '5 articles' in summary
        assert 'Technology & AI' in summary
        assert 'TechCrunch' in summary

    def test_handles_none_digest(self):
        """Test handling None digest info."""
        summary = generate_digest_summary(None)
        assert summary == ""

    def test_truncates_long_source_list(self):
        """Test that source lists are truncated."""
        digest_info = {
            'date_str': '2026-02-24',
            'article_count': 10,
            'categories': {
                '🔬 Technology & AI': {
                    'sources': ['Source1', 'Source2', 'Source3', 'Source4', 'Source5'],
                    'articles': [{'title': 'A', 'summary': 'S', 'source': 'Source1'}] * 10
                }
            }
        }

        summary = generate_digest_summary(digest_info)

        # Should only show first 3 sources
        assert 'Source1' in summary
        assert 'Source2' in summary
        assert 'Source3' in summary


# ---------------------------------------------------------------------------
# Test generate_period_summary
# ---------------------------------------------------------------------------

class TestGeneratePeriodSummary:
    def test_generates_monthly_summary(self):
        """Test generating a monthly summary."""
        period_digests = [
            {
                'date': datetime(2026, 2, 24),
                'date_str': '2026-02-24',
                'article_count': 10,
                'categories': {
                    '🔬 Technology & AI': {
                        'sources': ['TechCrunch'],
                        'articles': [{'title': 'A', 'summary': 'S', 'source': 'TechCrunch'}] * 10
                    }
                },
                'file_path': Path('docs/2026-02-24.md')
            },
            {
                'date': datetime(2026, 2, 25),
                'date_str': '2026-02-25',
                'article_count': 15,
                'categories': {
                    '🔬 Technology & AI': {
                        'sources': ['The Verge'],
                        'articles': [{'title': 'B', 'summary': 'T', 'source': 'The Verge'}] * 15
                    }
                },
                'file_path': Path('docs/2026-02-25.md')
            }
        ]

        summary = generate_period_summary(period_digests, 2026, 2)

        # Check metadata
        assert 'February 2026 Summary' in summary
        assert '**Total Days**: 2' in summary
        assert '**Total Articles**: 25' in summary
        assert '**Average Articles per Day**: 12' in summary  # 25 // 2 = 12

        # Check category breakdown
        assert 'Technology & AI' in summary
        assert 'Articles**: 25' in summary

        # Check daily summaries
        assert '2026-02-24' in summary
        assert '2026-02-25' in summary

    def test_includes_jekyll_front_matter(self):
        """Test that summary includes Jekyll front matter."""
        period_digests = [
            {
                'date': datetime(2026, 2, 24),
                'date_str': '2026-02-24',
                'article_count': 5,
                'categories': {},
                'file_path': Path('docs/2026-02-24.md')
            }
        ]

        summary = generate_period_summary(period_digests, 2026, 2)

        assert summary.startswith('---\nlayout: default')
        assert 'title: 📊 February 2026 Summary' in summary

    def test_aggregates_sources_correctly(self):
        """Test that sources are aggregated across multiple days."""
        period_digests = [
            {
                'date': datetime(2026, 2, 24),
                'date_str': '2026-02-24',
                'article_count': 5,
                'categories': {
                    '🔬 Technology & AI': {
                        'sources': ['TechCrunch', 'The Verge'],
                        'articles': [{'title': 'A', 'summary': 'S', 'source': 'TechCrunch'}] * 5
                    }
                },
                'file_path': Path('docs/2026-02-24.md')
            },
            {
                'date': datetime(2026, 2, 25),
                'date_str': '2026-02-25',
                'article_count': 3,
                'categories': {
                    '🔬 Technology & AI': {
                        'sources': ['TechCrunch', 'Hacker News'],
                        'articles': [{'title': 'B', 'summary': 'T', 'source': 'TechCrunch'}] * 3
                    }
                },
                'file_path': Path('docs/2026-02-25.md')
            }
        ]

        summary = generate_period_summary(period_digests, 2026, 2)

        # Should aggregate sources from both days
        assert 'TechCrunch' in summary
        assert 'The Verge' in summary
        assert 'Hacker News' in summary


# ---------------------------------------------------------------------------
# Test generate_summary_index
# ---------------------------------------------------------------------------

class TestGenerateSummaryIndex:
    def test_generates_index_with_links(self):
        """Test generating summary index with links."""
        all_summaries = [
            (2026, 2, 5),
            (2026, 1, 10),
            (2025, 12, 8),
        ]

        index = generate_summary_index(all_summaries)

        # Check metadata
        assert 'News Summaries' in index
        assert 'Monthly summaries of news digests' in index

        # Check links (should be sorted newest first)
        assert 'February 2026' in index
        assert 'January 2026' in index
        assert 'December 2025' in index

        # Check link format
        assert '(../../2026/02/summary.html)' in index
        assert '5 digests' in index
        assert '10 digests' in index

    def test_sorts_summaries_by_date(self):
        """Test that summaries are sorted newest first."""
        all_summaries = [
            (2025, 12, 5),
            (2026, 2, 3),
            (2026, 1, 7),
        ]

        index = generate_summary_index(all_summaries)

        # Find positions of months in the output
        feb_pos = index.find('February 2026')
        jan_pos = index.find('January 2026')
        dec_pos = index.find('December 2025')

        # February 2026 should come before January 2026, which should come before December 2025
        assert feb_pos < jan_pos < dec_pos

    def test_includes_jekyll_front_matter(self):
        """Test that index includes Jekyll front matter."""
        all_summaries = [(2026, 2, 5)]

        index = generate_summary_index(all_summaries)

        assert index.startswith('---\nlayout: default')
        assert 'title: 📊 News Summaries' in index

    def test_back_link_to_home(self):
        """Test that index includes back link to home."""
        all_summaries = [(2026, 2, 5)]

        index = generate_summary_index(all_summaries)

        assert '[← Back to Home](../../)' in index
