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
            "Test Source": [
                {
                    "title": "Breaking news",
                    "link": "https://example.com/article",
                    "summary": "Something happened.",
                    "published": "Fri, 15 Mar 2024 08:00:00 GMT",
                }
            ]
        }
        md = generate_markdown(FIXED_DATE, news)
        assert "[Breaking news](https://example.com/article)" in md
        assert "https://example.com/article" in md
        assert "Something happened." in md

    def test_source_heading_present(self):
        news = {"CNN": [{"title": "T", "link": "https://x.com", "summary": "", "published": ""}]}
        md = generate_markdown(FIXED_DATE, news)
        assert "## CNN" in md

    def test_article_without_link(self):
        news = {"Src": [{"title": "No link article", "link": "", "summary": "", "published": ""}]}
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
