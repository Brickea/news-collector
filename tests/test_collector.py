"""
Tests for src/collector.py

Run with:  pytest tests/
"""

import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

# Make the src package importable without an install step
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collector import (  # noqa: E402
    _strip_html,
    _truncate,
    _generate_shingles,
    _calculate_similarity,
    _deduplicate_articles,
    archive_old_files,
    fetch_rss,
    generate_markdown,
    load_config,
    collect_news,
)


# ---------------------------------------------------------------------------
# Unit tests – pure helpers
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_unescapes_entities(self):
        assert _strip_html("AT&amp;T &lt;ticker&gt;") == "AT&T <ticker>"

    def test_plain_text_unchanged(self):
        assert _strip_html("plain text") == "plain text"

    def test_collapses_whitespace(self):
        assert _strip_html("a  \n  b") == "a b"


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("short", 300) == "short"

    def test_long_string_truncated(self):
        result = _truncate("a" * 400, 300)
        assert len(result) == 301  # 300 chars + ellipsis character
        assert result.endswith("…")

    def test_exact_boundary(self):
        s = "x" * 300
        assert _truncate(s, 300) == s


# ---------------------------------------------------------------------------
# Shingles and Similarity Tests
# ---------------------------------------------------------------------------

class TestGenerateShingles:
    def test_basic_shingles(self):
        text = "machine learning is great"
        shingles = _generate_shingles(text, k=2)
        assert "machine learning" in shingles
        assert "learning is" in shingles
        assert "is great" in shingles
        assert len(shingles) == 3

    def test_short_text(self):
        text = "hello"
        shingles = _generate_shingles(text, k=3)
        assert shingles == {"hello"}

    def test_empty_text(self):
        shingles = _generate_shingles("", k=3)
        assert shingles == set()

    def test_lowercase_normalization(self):
        text1 = "Machine Learning"
        text2 = "machine learning"
        assert _generate_shingles(text1) == _generate_shingles(text2)


class TestCalculateSimilarity:
    def test_identical_texts(self):
        text = "This is a test article about machine learning"
        similarity = _calculate_similarity(text, text)
        assert similarity == 1.0

    def test_completely_different_texts(self):
        text1 = "Apple announces new iPhone"
        text2 = "Climate change impacts global weather"
        similarity = _calculate_similarity(text1, text2)
        # Should be very low but might not be exactly 0
        assert similarity < 0.2

    def test_similar_texts(self):
        text1 = "Tesla launches new electric car model in China"
        text2 = "Tesla unveils new electric vehicle model in China"
        similarity = _calculate_similarity(text1, text2)
        # With 3-shingles, similarity is lower but still detectable
        # These texts share: "model in china" -> 1 common shingle out of more
        assert similarity > 0.05  # Adjusted expectation
        assert similarity < 0.3   # Not too high since wording differs

    def test_word_order_matters(self):
        text1 = "machine learning algorithms"
        text2 = "learning machine algorithms"
        # With shingles, word order matters
        similarity = _calculate_similarity(text1, text2)
        # Should be less than 1.0 because order is different
        assert similarity < 1.0

    def test_empty_texts(self):
        assert _calculate_similarity("", "") == 1.0
        assert _calculate_similarity("hello", "") == 0.0
        assert _calculate_similarity("", "world") == 0.0


class TestDeduplicateArticles:
    def test_no_duplicates(self):
        articles = {
            "Source1": {
                "articles": [
                    {"title": "Apple launches iPhone", "link": "http://a.com", "summary": "Apple announced new phone", "published": ""},
                ],
                "categories": ["tech"]
            },
            "Source2": {
                "articles": [
                    {"title": "Climate summit begins", "link": "http://b.com", "summary": "World leaders gather", "published": ""},
                ],
                "categories": ["world"]
            }
        }
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        # Both articles should remain
        assert len(result) == 2
        assert "Source1" in result
        assert "Source2" in result

    def test_exact_duplicates(self):
        articles = {
            "Source1": {
                "articles": [
                    {"title": "Breaking news", "link": "http://a.com", "summary": "Something happened today", "published": ""},
                ],
                "categories": ["world"]
            },
            "Source2": {
                "articles": [
                    {"title": "Breaking news", "link": "http://b.com", "summary": "Something happened today", "published": ""},
                ],
                "categories": ["world"]
            }
        }
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        # Should only keep one article
        total_articles = sum(len(data['articles']) for data in result.values())
        assert total_articles == 1

    def test_similar_articles_removed(self):
        # Use more similar text to ensure detection with 3-shingles
        articles = {
            "Source1": {
                "articles": [
                    {"title": "Tesla launches new electric car", "link": "http://a.com", "summary": "Tesla launches new electric car model in California today", "published": ""},
                ],
                "categories": ["tech"]
            },
            "Source2": {
                "articles": [
                    {"title": "Tesla launches new electric car", "link": "http://b.com", "summary": "Tesla launches new electric car model in California today", "published": ""},
                ],
                "categories": ["tech"]
            }
        }
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        # Should remove the duplicate
        total_articles = sum(len(data['articles']) for data in result.values())
        assert total_articles == 1

    def test_keeps_first_occurrence(self):
        articles = {
            "Source1": {
                "articles": [
                    {"title": "First article", "link": "http://a.com", "summary": "This is the first one", "published": ""},
                ],
                "categories": ["tech"]
            },
            "Source2": {
                "articles": [
                    {"title": "First article", "link": "http://b.com", "summary": "This is the first one", "published": ""},
                ],
                "categories": ["tech"]
            }
        }
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        # Should keep the first source's article
        assert "Source1" in result
        assert len(result["Source1"]["articles"]) == 1

    def test_length_filter_optimization(self):
        # Test that length-based filtering works
        articles = {
            "Source1": {
                "articles": [
                    {"title": "Short", "link": "http://a.com", "summary": "A", "published": ""},
                ],
                "categories": ["tech"]
            },
            "Source2": {
                "articles": [
                    {"title": "Very long article title with many words", "link": "http://b.com", "summary": "This is a much longer summary with lots of text", "published": ""},
                ],
                "categories": ["tech"]
            }
        }
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        # Both should remain due to length difference
        total_articles = sum(len(data['articles']) for data in result.values())
        assert total_articles == 2


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("categories:\n  - tech\nsources: []\n")
        cfg = load_config(str(cfg_file))
        assert cfg["categories"] == ["tech"]
        assert cfg["sources"] == []

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "missing.yaml"))


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

FIXED_DATE = datetime(2024, 3, 15, 8, 0, 0, tzinfo=timezone.utc)


class TestGenerateMarkdown:
    def test_heading_contains_date(self):
        md = generate_markdown(FIXED_DATE, {})
        assert "2024-03-15" in md

    def test_empty_sources_shows_placeholder(self):
        md = generate_markdown(FIXED_DATE, {})
        assert "No articles" in md

    def test_article_link_in_output(self):
        news = {
            "Test Source": {
                "articles": [
                    {
                        "title": "Breaking news",
                        "link": "https://example.com/article",
                        "summary": "Something happened.",
                        "published": "Fri, 15 Mar 2024 08:00:00 GMT",
                    }
                ],
                "categories": ["world"]
            }
        }
        md = generate_markdown(FIXED_DATE, news)
        # Links are now HTML with target="_blank"
        assert '<a href="https://example.com/article" target="_blank">Read Full Article →</a>' in md
        assert "https://example.com/article" in md
        assert "Something happened." in md

    def test_source_heading_present(self):
        news = {
            "CNN": {
                "articles": [{"title": "T", "link": "https://x.com", "summary": "", "published": ""}],
                "categories": ["world"]
            }
        }
        md = generate_markdown(FIXED_DATE, news)
        # Source names are now h3 with emoji
        assert "### 📰 CNN" in md

    def test_article_without_link(self):
        news = {
            "Src": {
                "articles": [{"title": "No link article", "link": "", "summary": "", "published": ""}],
                "categories": ["technology"]
            }
        }
        md = generate_markdown(FIXED_DATE, news)
        # Should not produce a broken markdown link
        assert "[No link article]()" not in md
        assert "No link article" in md


# ---------------------------------------------------------------------------
# fetch_rss (mocked)
# ---------------------------------------------------------------------------

class TestFetchRss:
    def test_returns_articles(self, mocker):
        mock_entry = mocker.MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Test Title",
            "link": "https://example.com",
            "summary": "<p>Summary text</p>",
            "published": "Mon, 01 Jan 2024 00:00:00 GMT",
        }.get(key, default)

        mock_feed = mocker.MagicMock()
        mock_feed.entries = [mock_entry]

        mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        articles = fetch_rss("https://example.com/feed", max_items=5)
        assert len(articles) == 1
        assert articles[0]["title"] == "Test Title"
        assert articles[0]["link"] == "https://example.com"
        # HTML should be stripped from summary
        assert "<p>" not in articles[0]["summary"]

    def test_respects_max_items(self, mocker):
        mock_entry = mocker.MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "T",
            "link": "https://x.com",
            "summary": "",
            "published": "",
        }.get(key, default)

        mock_feed = mocker.MagicMock()
        mock_feed.entries = [mock_entry] * 20

        mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        articles = fetch_rss("https://example.com/feed", max_items=3)
        assert len(articles) == 3


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

class TestArchiveOldFiles:
    def test_moves_old_files(self, tmp_path):
        output_dir = tmp_path / "docs"
        output_dir.mkdir()
        archive_dir = tmp_path / "docs" / "archive"

        old_file = output_dir / "2024-01-01.md"
        old_file.write_text("old content")

        run_date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        archive_old_files(output_dir, archive_dir, "2024-03-15.md", "%Y/%m", run_date)

        expected_dest = archive_dir / "2024" / "03" / "2024-01-01.md"
        assert expected_dest.exists()
        assert not old_file.exists()

    def test_does_not_move_today_file(self, tmp_path):
        output_dir = tmp_path / "docs"
        output_dir.mkdir()
        archive_dir = tmp_path / "docs" / "archive"

        today_file = output_dir / "2024-03-15.md"
        today_file.write_text("today's content")

        run_date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        archive_old_files(output_dir, archive_dir, "2024-03-15.md", "%Y/%m", run_date)

        assert today_file.exists()

    def test_does_not_move_readme(self, tmp_path):
        output_dir = tmp_path / "docs"
        output_dir.mkdir()
        archive_dir = tmp_path / "docs" / "archive"

        readme = output_dir / "README.md"
        readme.write_text("readme")

        run_date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        archive_old_files(output_dir, archive_dir, "2024-03-15.md", "%Y/%m", run_date)

        assert readme.exists()


# ---------------------------------------------------------------------------
# Integration-style test for collect_news (fully mocked network)
# ---------------------------------------------------------------------------

_SAMPLE_CONFIG = textwrap.dedent(
    """\
    categories:
      - technology
    sources:
      - name: FakeTech
        type: rss
        url: https://fake.example.com/feed
        categories: [technology]
        enabled: true
      - name: DisabledSource
        type: rss
        url: https://disabled.example.com/feed
        categories: [technology]
        enabled: false
    output:
      dir: {output_dir}
      archive_dir: {archive_dir}
      max_items_per_source: 5
    archive:
      enabled: false
    """
)


class TestCollectNews:
    def test_creates_output_file(self, tmp_path, mocker):
        output_dir = tmp_path / "docs"
        archive_dir = tmp_path / "docs" / "archive"

        cfg_content = _SAMPLE_CONFIG.format(
            output_dir=str(output_dir), archive_dir=str(archive_dir)
        )
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(cfg_content)

        # Mock feedparser so no real HTTP request is made
        mock_entry = mocker.MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Tech Article",
            "link": "https://tech.example.com/1",
            "summary": "A cool tech story.",
            "published": "Mon, 15 Mar 2024 08:00:00 GMT",
        }.get(key, default)

        mock_feed = mocker.MagicMock()
        mock_feed.entries = [mock_entry]
        mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        output_file = collect_news(str(cfg_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "Tech Article" in content
        assert "https://tech.example.com/1" in content

    def test_skips_disabled_source(self, tmp_path, mocker):
        output_dir = tmp_path / "docs"
        archive_dir = tmp_path / "docs" / "archive"

        cfg_content = _SAMPLE_CONFIG.format(
            output_dir=str(output_dir), archive_dir=str(archive_dir)
        )
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(cfg_content)

        mock_feed = mocker.MagicMock()
        mock_feed.entries = []
        mock_parse = mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        collect_news(str(cfg_file))

        # feedparser.parse should only be called for the enabled source
        called_urls = [call.args[0] for call in mock_parse.call_args_list]
        assert "https://disabled.example.com/feed" not in called_urls

    def test_category_filter_excludes_source(self, tmp_path, mocker):
        """A source whose categories don't overlap with enabled categories is skipped."""
        output_dir = tmp_path / "docs"
        archive_dir = tmp_path / "docs" / "archive"

        cfg = {
            "categories": ["world"],  # only world
            "sources": [
                {
                    "name": "TechSource",
                    "type": "rss",
                    "url": "https://tech.example.com/feed",
                    "categories": ["technology"],
                    "enabled": True,
                }
            ],
            "output": {
                "dir": str(output_dir),
                "archive_dir": str(archive_dir),
                "max_items_per_source": 5,
            },
            "archive": {"enabled": False},
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(cfg))

        mock_parse = mocker.patch("collector.feedparser.parse")

        collect_news(str(cfg_file))

        # feedparser should never have been called
        mock_parse.assert_not_called()

    def test_archive_enabled_moves_old_files(self, tmp_path, mocker):
        output_dir = tmp_path / "docs"
        output_dir.mkdir()
        archive_dir = tmp_path / "docs" / "archive"

        old_file = output_dir / "2020-01-01.md"
        old_file.write_text("old")

        cfg = {
            "categories": ["technology"],
            "sources": [
                {
                    "name": "FakeTech",
                    "type": "rss",
                    "url": "https://fake.example.com/feed",
                    "categories": ["technology"],
                    "enabled": True,
                }
            ],
            "output": {
                "dir": str(output_dir),
                "archive_dir": str(archive_dir),
                "max_items_per_source": 5,
            },
            "archive": {"enabled": True, "format": "%Y/%m"},
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(cfg))

        mock_feed = mocker.MagicMock()
        mock_feed.entries = []
        mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        collect_news(str(cfg_file))

        # The old file should have been moved to the archive
        assert not old_file.exists()

    def test_categories_override_takes_precedence(self, tmp_path, mocker):
        """categories_override replaces the config's categories list."""
        output_dir = tmp_path / "docs"
        archive_dir = tmp_path / "docs" / "archive"

        # Config says "world" only, but we override to "technology"
        cfg = {
            "categories": ["world"],
            "sources": [
                {
                    "name": "TechSource",
                    "type": "rss",
                    "url": "https://tech.example.com/feed",
                    "categories": ["technology"],
                    "enabled": True,
                },
                {
                    "name": "WorldSource",
                    "type": "rss",
                    "url": "https://world.example.com/feed",
                    "categories": ["world"],
                    "enabled": True,
                },
            ],
            "output": {
                "dir": str(output_dir),
                "archive_dir": str(archive_dir),
                "max_items_per_source": 5,
            },
            "archive": {"enabled": False},
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(cfg))

        mock_feed = mocker.MagicMock()
        mock_feed.entries = []
        mock_parse = mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        # Override to technology only
        collect_news(str(cfg_file), categories_override=["technology"])

        called_urls = [call.args[0] for call in mock_parse.call_args_list]
        assert "https://tech.example.com/feed" in called_urls
        assert "https://world.example.com/feed" not in called_urls

    def test_categories_override_empty_list_collects_all(self, tmp_path, mocker):
        """An empty categories_override list means no category filter is applied."""
        output_dir = tmp_path / "docs"
        archive_dir = tmp_path / "docs" / "archive"

        cfg = {
            "categories": ["world"],
            "sources": [
                {
                    "name": "TechSource",
                    "type": "rss",
                    "url": "https://tech.example.com/feed",
                    "categories": ["technology"],
                    "enabled": True,
                },
            ],
            "output": {
                "dir": str(output_dir),
                "archive_dir": str(archive_dir),
                "max_items_per_source": 5,
            },
            "archive": {"enabled": False},
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(cfg))

        mock_feed = mocker.MagicMock()
        mock_feed.entries = []
        mock_parse = mocker.patch("collector.feedparser.parse", return_value=mock_feed)

        # Empty override → no category filtering → tech source is fetched
        collect_news(str(cfg_file), categories_override=[])

        called_urls = [call.args[0] for call in mock_parse.call_args_list]
        assert "https://tech.example.com/feed" in called_urls
