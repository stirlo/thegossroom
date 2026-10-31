#!/usr/bin/env python3
"""Regression tests for removed-article related-story recovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

# Keep the test runnable directly and through unittest discovery without
# turning the operational scripts directory into an importable package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_recovery_index import Story, best_replacement, build_index, public_stories


def story(path: str, tags: tuple[str, ...], heat: float, timestamp: float = 0) -> Story:
    """Create a compact story fixture with stable metadata."""

    primary = tags[0] if tags else ""
    return Story(path, path, tags, primary, timestamp, heat)


class RecoveryRankingTests(unittest.TestCase):
    """Protect the all-tags-first fallback contract requested for TGR."""

    def test_all_tags_beat_hotter_partial_match(self) -> None:
        """Prefer Kim-and-Kanye coverage over a hotter Kanye-only story."""

        removed = story("/old/", ("kim_kardashian", "kanye_west"), 0)
        combined = story("/combined/", ("kim_kardashian", "kanye_west"), 20)
        kanye_only = story("/kanye/", ("kanye_west",), 100)
        self.assertEqual(best_replacement(removed, [kanye_only, combined]), combined)

    def test_partial_tag_match_beats_unrelated_story(self) -> None:
        """Fall back to a Kanye story when no combined match remains live."""

        removed = story("/old/", ("kim_kardashian", "kanye_west"), 0)
        kanye_only = story("/kanye/", ("kanye_west",), 30)
        unrelated = story("/unrelated/", ("taylor_swift",), 100)
        self.assertEqual(best_replacement(removed, [unrelated, kanye_only]), kanye_only)

    def test_primary_tag_beats_multiple_lower_priority_tags(self) -> None:
        """Use MAIN before SECOND/THIRD when the complete combination is unavailable."""

        removed = story("/old/", ("kim_kardashian", "kanye_west", "fashion"), 0)
        main_only = story("/kim/", ("kim_kardashian",), 20)
        lower_tags = story("/kanye-fashion/", ("kanye_west", "fashion"), 100)
        self.assertEqual(best_replacement(removed, [lower_tags, main_only]), main_only)

    def test_index_points_removed_path_into_live_catalog(self) -> None:
        """Keep the public index compact by storing live-story array positions."""

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for directory in ("_posts", "_archive", "_cold_storage"):
                (base / directory).mkdir()
            (base / "_posts" / "2026-10-31-kim-and-kanye.md").write_text(
                "---\n"
                "title: Kim and Kanye update\n"
                "tags: [kim_kardashian, kanye_west]\n"
                "temperature: 40\n"
                "---\n",
                encoding="utf-8",
            )
            (base / "_archive" / "2026-01-01-old-kim-and-kanye.md").write_text(
                "---\n"
                "title: Old Kim and Kanye story\n"
                "tags: [kim_kardashian, kanye_west]\n"
                "---\n",
                encoding="utf-8",
            )

            payload = build_index(base)

        position = payload["redirects"]["/2026/01/01/old-kim-and-kanye/"]
        self.assertIsInstance(position, int)
        self.assertEqual(payload["live"][position]["url"], "/2026/10/31/kim-and-kanye/")

    def test_public_catalog_matches_jekyll_limit_and_future_rules(self) -> None:
        """Never redirect to a source post that Jekyll did not publish."""

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "_posts").mkdir()
            (base / "_config.yml").write_text(
                "limit_posts: 2\nfuture: false\n",
                encoding="utf-8",
            )
            for name in (
                "2026-10-29-older.md",
                "2026-10-30-newest.md",
                "2099-01-01-future.md",
            ):
                (base / "_posts" / name).write_text(
                    f"---\ntitle: {name}\ntags: [example]\n---\n",
                    encoding="utf-8",
                )

            stories = public_stories(base)

        self.assertEqual([item.path for item in stories], ["/2026/10/30/newest/"])


if __name__ == "__main__":
    unittest.main()
