#!/usr/bin/env python3
"""
TGR Scripts Cleanup
Retires emergency/legacy scripts that are no longer needed.
Moves them to scripts/_retired/ rather than deleting in case anything references them.

Run from: ~/www/thegossroom/
Usage: python3 tgr_retire_scripts.py [--dry-run]
"""

import sys
import shutil
import argparse
from pathlib import Path

RETIRE = [
    # Emergency firefighting tools — replaced by Harold SQLite + clean pipeline
    "emergency_cleanup.py",
    "auto_fix_posts.py",
    "recover_posts.py",
    "fix_yaml.py",
    "fix_bluesky_urls.py",
    # Legacy duplicates — replaced by harold_run.py orchestration
    "run_all.py",
    "temperature_calculator.py",      # duplicate of drama_temperature_calculator.py
    # celebrity_discovery.py is subsumed into enhanced_gossip_scraper.py
    "celebrity_discovery.py",
]

KEEP_NOTE = """# Retired Scripts

These scripts were moved here during the Harold migration (2026-06-20).

They were emergency/legacy tools from the GitHub Actions era.
The Harold cron pipeline (harold_run.py) replaces all of them cleanly.

DO NOT restore these to scripts/ — they write directly to celebrities.yml
which is now a read-only Jekyll snapshot. Harold SQLite is the source of truth.
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", default=".")
    args = parser.parse_args()

    base = Path(args.path).resolve()
    scripts_dir = base / "scripts"
    retired_dir = scripts_dir / "_retired"

    if not scripts_dir.exists():
        print(f"scripts/ not found at {base}")
        sys.exit(1)

    if not args.dry_run:
        retired_dir.mkdir(exist_ok=True)
        (retired_dir / "README.md").write_text(KEEP_NOTE)

    moved = 0
    for name in RETIRE:
        src = scripts_dir / name
        if not src.exists():
            print(f"  SKIP (not found): {name}")
            continue

        dst = retired_dir / name
        if args.dry_run:
            print(f"  DRY RUN: would retire {name}")
        else:
            shutil.move(str(src), str(dst))
            print(f"  Retired: {name}")
            moved += 1

    if not args.dry_run:
        print(f"\nRetired {moved} scripts to scripts/_retired/")
        print("\nscripts/ now contains:")
        for f in sorted(scripts_dir.glob("*.py")):
            print(f"  {f.name}")
    else:
        print(f"\nDRY RUN: would retire {len([n for n in RETIRE if (scripts_dir/n).exists()])} scripts")

if __name__ == "__main__":
    main()
