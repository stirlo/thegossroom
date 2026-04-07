#!/usr/bin/env python3
"""
fix_bluesky_urls.py — Repair historical broken Bluesky post URLs.

The GossRoom Bluesky poster generated URLs by slugifying post filenames.
Jekyll generates URLs from post titles. When titles contained special chars
or the filename was truncated at 50 chars, the two diverged → broken links.

This script:
1. Reads _data/bluesky_posted.yml (historical post tracking)
2. For each posted filename, generates both the filename-slug URL and
   the actual Jekyll permalink from the frontmatter slug/title
3. Where they differ, adds a redirect_from: entry to the post frontmatter
   so any old Bluesky link redirects to the correct post via jekyll-redirect-from
4. Writes a report of everything it fixed / couldn't fix

Run from the thegossroom repo root:
    python3 scripts/fix_bluesky_urls.py [--dry-run] [--verbose]
"""

import re
import sys
import yaml
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SITE_BASE    = "https://thegossroom.com"
POSTS_DIR    = Path("_posts")
DATA_DIR     = Path("_data")
POSTED_FILE  = DATA_DIR / "bluesky_posted.yml"
REPORT_FILE  = DATA_DIR / "url_repair_report.yml"


# ── Helpers ──────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """Jekyll-compatible slugify: lowercase, strip non-alphanumeric, collapse hyphens."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def url_from_filename(filename: str) -> str:
    """Generate the URL the old poster would have constructed from a filename."""
    stem = filename.replace(".md", "")
    if len(stem) < 11:
        return SITE_BASE + "/"
    date_part = stem[:10]
    slug_part = stem[11:]
    slug_part = re.sub(r"-+", "-", slug_part).strip("-")
    try:
        year, month, day = date_part.split("-")
        return f"{SITE_BASE}/{year}/{month}/{day}/{slug_part}/"
    except ValueError:
        return SITE_BASE + "/"


def url_from_frontmatter(filename: str, frontmatter: dict) -> str:
    """Generate the URL Jekyll actually uses, from frontmatter fields."""
    stem = filename.replace(".md", "")
    if len(stem) < 11:
        return None
    date_part = stem[:10]
    try:
        year, month, day = date_part.split("-")
    except ValueError:
        return None

    # Prefer explicit permalink or slug
    if frontmatter.get("permalink"):
        perm = frontmatter["permalink"].strip("/")
        return f"{SITE_BASE}/{perm}/"
    if frontmatter.get("slug"):
        slug = frontmatter["slug"].strip()
        return f"{SITE_BASE}/{year}/{month}/{day}/{slug}/"

    # Derive from title (what Jekyll actually does)
    title = frontmatter.get("title", "")
    if not title:
        return None
    slug = slugify(str(title))
    return f"{SITE_BASE}/{year}/{month}/{day}/{slug}/"


def load_posted_tracking() -> list:
    """Load bluesky_posted.yml — handles both old list format and new dict format."""
    if not POSTED_FILE.exists():
        print(f"⚠️  {POSTED_FILE} not found — nothing to repair")
        return []
    with open(POSTED_FILE) as f:
        data = yaml.safe_load(f) or {}
    if isinstance(data, list):
        return data  # old format: list of filenames
    elif isinstance(data, dict):
        return list(data.get("posted_items", {}).keys())
    return []


def parse_post(post_path: Path) -> dict | None:
    """Parse a Jekyll post file, return {frontmatter, body, raw_fm_text}."""
    try:
        content = post_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ✗ Could not read {post_path.name}: {e}")
        return None

    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        print(f"  ✗ YAML error in {post_path.name}: {e}")
        return None
    return {"frontmatter": fm, "body": parts[2], "raw_fm": parts[1]}


def add_redirect_to_post(post_path: Path, broken_path: str, dry_run: bool) -> bool:
    """
    Add redirect_from: [broken_path] to the post's frontmatter.
    The broken_path is just the /YYYY/MM/DD/slug/ part (no domain).
    """
    parsed = parse_post(post_path)
    if not parsed:
        return False

    fm = parsed["frontmatter"]
    existing_redirects = fm.get("redirect_from", [])

    # Normalise to list
    if isinstance(existing_redirects, str):
        existing_redirects = [existing_redirects]
    elif existing_redirects is None:
        existing_redirects = []

    if broken_path in existing_redirects:
        return False  # already has the redirect

    existing_redirects.append(broken_path)
    fm["redirect_from"] = existing_redirects

    if dry_run:
        return True  # would have fixed it

    # Reconstruct the file
    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    new_content = f"---\n{new_fm}---\n{parsed['body']}"
    post_path.write_text(new_content, encoding="utf-8")
    return True


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fix broken historical Bluesky URLs via redirect_from")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    parser.add_argument("--verbose", action="store_true", help="Print every post checked")
    args = parser.parse_args()

    dry = args.dry_run
    verbose = args.verbose

    if dry:
        print("🔍 DRY RUN — no files will be modified\n")

    posted_filenames = load_posted_tracking()
    print(f"📋 Found {len(posted_filenames)} historically posted filenames\n")

    fixed      = []
    skipped    = []
    not_found  = []
    already_ok = []

    for filename in posted_filenames:
        # Normalise — tracking may store full paths or just filenames
        fname = Path(filename).name
        post_path = POSTS_DIR / fname

        if not post_path.exists():
            # Try archive dir
            archive_path = Path("_archive") / fname
            if archive_path.exists():
                post_path = archive_path
            else:
                not_found.append(fname)
                if verbose:
                    print(f"  ✗ NOT FOUND: {fname}")
                continue

        parsed = parse_post(post_path)
        if not parsed:
            skipped.append(fname)
            continue

        old_url     = url_from_filename(fname)
        correct_url = url_from_frontmatter(fname, parsed["frontmatter"])

        if not correct_url:
            skipped.append(fname)
            if verbose:
                print(f"  ? SKIP (no title/slug): {fname}")
            continue

        if old_url == correct_url:
            already_ok.append(fname)
            if verbose:
                print(f"  ✓ OK: {fname}")
            continue

        # URLs differ — add redirect from the broken path to the correct one
        broken_path = old_url.replace(SITE_BASE, "")

        if verbose or dry:
            print(f"  🔧 FIX: {fname}")
            print(f"       broken:  {old_url}")
            print(f"       correct: {correct_url}")
            print(f"       adding redirect_from: {broken_path}")

        result = add_redirect_to_post(post_path, broken_path, dry_run=dry)
        if result:
            fixed.append({
                "file": fname,
                "broken_url": old_url,
                "correct_url": correct_url,
                "redirect_added": broken_path
            })
        else:
            skipped.append(fname)

    # ── Report ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  URL REPAIR COMPLETE {'(DRY RUN)' if dry else ''}")
    print(f"{'='*60}")
    print(f"  ✅  Fixed:       {len(fixed)}")
    print(f"  ✓   Already OK:  {len(already_ok)}")
    print(f"  ✗   Not found:   {len(not_found)}")
    print(f"  ?   Skipped:     {len(skipped)}")
    print(f"{'='*60}\n")

    if fixed and not dry:
        report = {
            "generated": datetime.utcnow().isoformat(),
            "total_fixed": len(fixed),
            "fixes": fixed,
            "not_found": not_found,
        }
        DATA_DIR.mkdir(exist_ok=True)
        with open(REPORT_FILE, "w") as f:
            yaml.dump(report, f, default_flow_style=False, allow_unicode=True)
        print(f"📄 Report written to {REPORT_FILE}")
        print(f"\n💡 Next: commit and push — GitHub Pages will serve redirects automatically.")
        print(f"   jekyll-redirect-from is already in the Gemfile so no setup needed.\n")
    elif fixed and dry:
        print(f"💡 Run without --dry-run to apply {len(fixed)} fixes.\n")


if __name__ == "__main__":
    main()
