"""
Tests for src/generate_index.py

Run with:  pytest tests/
"""

import sys
from datetime import datetime
from pathlib import Path

# Make the src package importable without an install step
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from generate_index import generate_period_index  # noqa: E402


def test_period_index_links_to_root_digest(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    period_dir = docs_dir / "archive" / "2026" / "02"
    period_dir.mkdir(parents=True)

    digest_path = docs_dir / "2026-02-24.md"
    digest_path.write_text("content", encoding="utf-8")

    content = generate_period_index(
        2026,
        2,
        [(datetime(2026, 2, 24), "2026-02-24.md")],
        docs_dir,
    )

    assert "- [2026-02-24](../../../2026-02-24.html) - Tuesday" in content
