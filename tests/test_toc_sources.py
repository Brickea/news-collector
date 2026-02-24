"""
Tests for Table of Contents source-level links feature.

This ensures that when news sources are added/removed from the config,
the TOC automatically includes appropriate source-level links.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make the src package importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collector import generate_markdown, _create_anchor  # noqa: E402


class TestCreateAnchor:
    """Test the anchor generation helper."""

    def test_removes_emojis(self):
        assert _create_anchor("📰 NASA Breaking News") == "nasa-breaking-news"
        assert _create_anchor("🔬 Technology & AI") == "technology-ai"

    def test_handles_special_characters(self):
        assert _create_anchor("Stack Overflow Blog") == "stack-overflow-blog"
        assert _create_anchor("Dev.to") == "devto"

    def test_removes_ampersands(self):
        assert _create_anchor("Business & Finance") == "business-finance"

    def test_multiple_spaces(self):
        assert _create_anchor("Multiple   Spaces   Here") == "multiple-spaces-here"

    def test_consecutive_hyphens(self):
        # After removing special chars, we might get consecutive hyphens
        result = _create_anchor("Test--Multiple---Hyphens")
        assert result == "test-multiple-hyphens"


class TestTocSourceLinks:
    """Test that TOC includes source-level links."""

    def test_toc_includes_sources_under_categories(self):
        """TOC should show sources nested under their categories."""
        news = {
            "TechCrunch": {
                "articles": [
                    {
                        "title": "Test",
                        "link": "http://example.com",
                        "summary": "Summary",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            },
            "NASA Breaking News": {
                "articles": [
                    {
                        "title": "Test",
                        "link": "http://example.com",
                        "summary": "Summary",
                        "published": "",
                    }
                ],
                "categories": ["science"],
            },
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news, translator=None)

        # Check that TOC contains source links
        assert "- [TechCrunch](#techcrunch)" in md
        assert "- [NASA Breaking News](#nasa-breaking-news)" in md

        # Check that sources are indented (nested under categories)
        assert "  - [TechCrunch](#techcrunch)" in md
        assert "  - [NASA Breaking News](#nasa-breaking-news)" in md

    def test_source_anchors_match_headings(self):
        """Source anchor links should match the actual source headings."""
        news = {
            "The Verge": {
                "articles": [
                    {
                        "title": "Test",
                        "link": "http://example.com",
                        "summary": "Summary",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            }
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news, translator=None)

        # TOC link
        assert "- [The Verge](#the-verge)" in md
        # Actual heading
        assert "### 📰 The Verge" in md

    def test_multiple_sources_same_category(self):
        """Multiple sources in the same category should all appear in TOC."""
        news = {
            "Source1": {
                "articles": [
                    {
                        "title": "T1",
                        "link": "http://a.com",
                        "summary": "S1",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            },
            "Source2": {
                "articles": [
                    {
                        "title": "T2",
                        "link": "http://b.com",
                        "summary": "S2",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            },
            "Source3": {
                "articles": [
                    {
                        "title": "T3",
                        "link": "http://c.com",
                        "summary": "S3",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            },
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news, translator=None)

        # All three sources should appear
        assert "  - [Source1](#source1)" in md
        assert "  - [Source2](#source2)" in md
        assert "  - [Source3](#source3)" in md

    def test_empty_articles_not_in_toc(self):
        """Sources with no articles should not appear in TOC."""
        news = {
            "Source1": {"articles": [], "categories": ["technology"]},
            "Source2": {
                "articles": [
                    {
                        "title": "T",
                        "link": "http://a.com",
                        "summary": "S",
                        "published": "",
                    }
                ],
                "categories": ["technology"],
            },
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news, translator=None)

        # Source1 has no articles, should not be in TOC
        assert "Source1" not in md
        # Source2 has articles, should be in TOC
        assert "- [Source2](#source2)" in md

    def test_toc_structure_with_all_categories(self):
        """Verify TOC structure when all categories have sources."""
        news = {
            "TechCrunch": {
                "articles": [
                    {"title": "T", "link": "http://a.com", "summary": "S", "published": ""}
                ],
                "categories": ["technology"],
            },
            "Dev.to": {
                "articles": [
                    {"title": "T", "link": "http://b.com", "summary": "S", "published": ""}
                ],
                "categories": ["coding"],
            },
            "Financial Times": {
                "articles": [
                    {"title": "T", "link": "http://c.com", "summary": "S", "published": ""}
                ],
                "categories": ["business"],
            },
            "BBC News": {
                "articles": [
                    {"title": "T", "link": "http://d.com", "summary": "S", "published": ""}
                ],
                "categories": ["world"],
            },
            "WHO News": {
                "articles": [
                    {"title": "T", "link": "http://e.com", "summary": "S", "published": ""}
                ],
                "categories": ["health"],
            },
            "NASA Breaking News": {
                "articles": [
                    {"title": "T", "link": "http://f.com", "summary": "S", "published": ""}
                ],
                "categories": ["science"],
            },
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news, translator=None)

        # Verify TOC has all categories
        assert "🔬 Technology & AI" in md
        assert "💻 Coding & Development" in md
        assert "💼 Business & Finance" in md
        assert "🌍 World News" in md
        assert "🏥 Health" in md
        assert "🔭 Science" in md

        # Verify TOC has all sources nested under categories
        assert "  - [TechCrunch](#techcrunch)" in md
        assert "  - [Dev.to](#devto)" in md
        assert "  - [Financial Times](#financial-times)" in md
        assert "  - [BBC News](#bbc-news)" in md
        assert "  - [WHO News](#who-news)" in md
        assert "  - [NASA Breaking News](#nasa-breaking-news)" in md

    def test_config_changes_reflected_in_toc(self):
        """When sources change in config, TOC should update automatically."""
        # Simulate adding a new source
        news_with_new_source = {
            "TechCrunch": {
                "articles": [
                    {"title": "T", "link": "http://a.com", "summary": "S", "published": ""}
                ],
                "categories": ["technology"],
            },
            "NewTechBlog": {  # New source added to config
                "articles": [
                    {"title": "T", "link": "http://b.com", "summary": "S", "published": ""}
                ],
                "categories": ["technology"],
            },
        }

        date = datetime(2026, 2, 24, tzinfo=timezone.utc)
        md = generate_markdown(date, news_with_new_source, translator=None)

        # New source should appear in TOC
        assert "- [NewTechBlog](#newtechblog)" in md
        assert "### 📰 NewTechBlog" in md
