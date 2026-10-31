#!/usr/bin/env python3
"""Build the compact related-story index used by The Goss Room's 404 recovery."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DATE_PREFIX_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>.+)\.md$")
NON_TAG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Story:
    """Represent only the metadata needed to rank a live replacement story."""

    path: str
    title: str
    tags: tuple[str, ...]
    primary: str
    timestamp: float
    heat: float


def normalise_tag(value: Any) -> str:
    """Return one stable celebrity/topic key across spaces, dashes, and underscores."""

    return NON_TAG_RE.sub("_", str(value).strip().lower()).strip("_")


def read_front_matter(path: Path) -> dict[str, Any] | None:
    """Read a Markdown file's YAML header without loading its article body."""

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            if handle.readline().strip() != "---":
                return None
            header: list[str] = []
            for line in handle:
                if line.strip() == "---":
                    break
                header.append(line)
            else:
                return None
        data = yaml.safe_load("".join(header)) or {}
        return data if isinstance(data, dict) else None
    except (OSError, yaml.YAMLError):
        return None


def story_path(path: Path, metadata: dict[str, Any]) -> str | None:
    """Reconstruct the canonical Jekyll article URL from its retained filename."""

    match = DATE_PREFIX_RE.match(path.name)
    if not match:
        return None
    year, month, day = match.group("date").split("-")
    slug = str(metadata.get("slug") or match.group("slug")).strip("/")
    return f"/{year}/{month}/{day}/{slug}/"


def story_tags(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return up to four unique tags in primary, explicit, then inferred order."""

    values: list[Any] = []
    if metadata.get("primary_celebrity"):
        values.append(metadata["primary_celebrity"])
    raw_tags = metadata.get("tags") or []
    values.extend(raw_tags if isinstance(raw_tags, list) else [raw_tags])
    for field in ("mentions", "celebrity_temps"):
        mapping = metadata.get(field) or {}
        if isinstance(mapping, dict):
            values.extend(mapping.keys())
    ordered: list[str] = []
    for value in values:
        tag = normalise_tag(value)
        if tag and tag not in ordered:
            ordered.append(tag)
    return tuple(ordered[:4])


def parse_timestamp(metadata: dict[str, Any], path: Path) -> float:
    """Return a comparable publication timestamp with a filename-date fallback."""

    raw_date = metadata.get("date")
    if isinstance(raw_date, datetime):
        parsed = raw_date
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    if raw_date:
        try:
            parsed = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    match = DATE_PREFIX_RE.match(path.name)
    if match:
        parsed = datetime.strptime(match.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return 0.0


def load_story(path: Path) -> Story | None:
    """Load one story record, returning None for malformed or non-post files."""

    metadata = read_front_matter(path)
    if metadata is None:
        return None
    canonical_path = story_path(path, metadata)
    if canonical_path is None:
        return None
    heat = metadata.get("temperature", metadata.get("drama_score", 0))
    try:
        numeric_heat = float(heat or 0)
    except (TypeError, ValueError):
        numeric_heat = 0.0
    return Story(
        path=canonical_path,
        title=str(metadata.get("title") or "Related story"),
        tags=story_tags(metadata),
        primary=normalise_tag(metadata.get("primary_celebrity") or ""),
        timestamp=parse_timestamp(metadata, path),
        heat=numeric_heat,
    )


def rank_candidate(removed: Story, candidate: Story) -> tuple[Any, ...]:
    """Rank all-tag matches before broader celebrity matches, heat, and recency."""

    removed_tags = set(removed.tags)
    candidate_tags = set(candidate.tags)
    overlap = removed_tags & candidate_tags
    all_tags = bool(removed_tags) and removed_tags <= candidate_tags
    coverage = len(overlap) / len(removed.tags) if removed.tags else 0.0
    # A lexicographic presence vector preserves MAIN -> SECOND -> THIRD ->
    # FOURTH priority when no live story contains the complete combination.
    priority_matches = tuple(tag in candidate_tags for tag in removed.tags)
    return (
        all_tags,
        priority_matches,
        len(overlap),
        coverage,
        candidate.heat,
        candidate.timestamp,
    )


def best_replacement(removed: Story, active: list[Story]) -> Story | None:
    """Choose a live story sharing metadata, or the newest live story as a last resort."""

    if not active:
        return None
    removed_tags = set(removed.tags)
    tagged = [candidate for candidate in active if removed_tags & set(candidate.tags)]
    pool = tagged or active
    return max(pool, key=lambda candidate: rank_candidate(removed, candidate))


def iter_markdown(directory: Path) -> list[Path]:
    """Return retained Markdown posts in deterministic filename order."""

    return sorted(directory.glob("*.md")) if directory.exists() else []


def public_stories(base: Path) -> list[Story]:
    """Mirror Jekyll's future and limit_posts rules so every target really exists."""

    config = read_front_matter(base / "_config.yml")
    if config is None:
        try:
            config = yaml.safe_load((base / "_config.yml").read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            config = {}
    stories = [story for path in iter_markdown(base / "_posts") if (story := load_story(path))]
    stories.sort(key=lambda item: item.timestamp, reverse=True)
    try:
        limit = int(config.get("limit_posts") or 0)
    except (TypeError, ValueError):
        limit = 0
    if limit > 0:
        # Jekyll applies limit_posts before suppressing future-dated output, so
        # future stories consume slots instead of pulling older stories forward.
        stories = stories[:limit]
    if not config.get("future", False):
        now = datetime.now(timezone.utc).timestamp()
        stories = [story for story in stories if story.timestamp <= now]
    return stories


def build_index(base: Path) -> dict[str, Any]:
    """Build removed-path redirects plus a small live fallback search catalog."""

    active = public_stories(base)
    ranked_active = sorted(active, key=lambda item: (item.heat, item.timestamp), reverse=True)
    live_position = {story.path: index for index, story in enumerate(ranked_active)}
    removed_paths = iter_markdown(base / "_archive") + iter_markdown(base / "_cold_storage")
    # Store an integer into the live array instead of repeating long titles and
    # URLs tens of thousands of times. Cloudflare can compress this map well.
    redirects: dict[str, int] = {}
    malformed = 0

    for path in removed_paths:
        removed = load_story(path)
        if removed is None:
            malformed += 1
            continue
        replacement = best_replacement(removed, active)
        if replacement is None:
            continue
        redirects[removed.path] = live_position[replacement.path]

    live = [
        {
            "url": story.path,
            "title": story.title,
            "tags": list(story.tags),
            "heat": story.heat,
            "date": story.timestamp,
        }
        for story in ranked_active
    ]
    return {
        "version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "redirects": redirects,
        "live": live,
        "stats": {
            "active": len(active),
            "removed": len(redirects),
            "malformed": malformed,
        },
    }


def write_index(base: Path, output: Path) -> dict[str, Any]:
    """Write the index atomically so a failed run cannot truncate the live artifact."""

    payload = build_index(base)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(output)
    return payload


def main() -> int:
    """Parse CLI options, build the index, and report concise coverage statistics."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    base = args.base.resolve()
    output = (args.output or (base / "recovery-index.json")).resolve()
    payload = write_index(base, output)
    stats = payload["stats"]
    print(
        f"Recovery index: {stats['removed']} removed routes, "
        f"{stats['active']} live stories, {stats['malformed']} malformed files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
