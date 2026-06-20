#!/usr/bin/env python3
"""
TGR Celebrity Deduplication
Finds likely duplicate celebrity entries (eg adele / adele_adkins)
and sets canonical_key so boosts merge rather than double-count.

Run from: ~/www/thegossroom/
Usage:
  python3 tgr_dedup_celebs.py --dry-run   # preview merges
  python3 tgr_dedup_celebs.py             # apply merges to SQLite
  python3 tgr_dedup_celebs.py --show      # just show all duplicates found
"""

import sqlite3
import argparse
import re
from pathlib import Path
from collections import defaultdict

DRY_RUN = False

def normalise(name: str) -> str:
    """Reduce a name to its core tokens for fuzzy matching."""
    name = name.lower().replace("_", " ").strip()
    # Remove common suffixes that create duplicates
    suffixes = [" jr", " sr", " ii", " iii", " iv"]
    for s in suffixes:
        if name.endswith(s):
            name = name[:-len(s)].strip()
    return name

def first_last(name: str) -> tuple:
    """Return (first, last) tokens from a normalised name."""
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return parts[0], ""

def find_duplicates(rows: list) -> list:
    """
    Find groups of celebrity keys that refer to the same person.
    Strategy:
      1. Exact first+last match across keys with different middle names
         eg 'jennifer_lopez' and 'jennifer_lynn_lopez'
      2. One name is a strict prefix/suffix of another
         eg 'adele' and 'adele_adkins'
      3. Known manual pairs (hardcoded for common gossip fixtures)
    Returns list of (canonical_key, [alias_keys]) tuples.
    """
    # Build lookup: normalised_name -> list of keys
    by_name = defaultdict(list)
    for key, display_name in rows:
        norm = normalise(display_name or key)
        by_name[norm].append(key)

    # Build first+last lookup
    by_first_last = defaultdict(list)
    for key, display_name in rows:
        norm = normalise(display_name or key)
        fl = first_last(norm)
        if fl[0] and fl[1]:  # only index if we have both
            by_first_last[fl].append(key)

    groups = {}  # canonical_key -> set of alias keys

    # Strategy 1: exact normalised name match (different keys, same display)
    for norm, keys in by_name.items():
        if len(keys) > 1:
            # Shortest key is usually the canonical one (eg 'adele' vs 'adele_adkins')
            keys_sorted = sorted(keys, key=len)
            canonical = keys_sorted[0]
            aliases = keys_sorted[1:]
            if canonical not in groups:
                groups[canonical] = set()
            groups[canonical].update(aliases)

    # Strategy 2: first+last match (catches middle names)
    for fl, keys in by_first_last.items():
        if len(keys) > 1:
            keys_sorted = sorted(keys, key=len)
            canonical = keys_sorted[0]
            aliases = keys_sorted[1:]
            if canonical not in groups:
                groups[canonical] = set()
            groups[canonical].update(aliases)

    # Strategy 3: one key is substring of another
    # Only for single-word keys that look like first names (not common nouns)
    # Blacklist: single words that are not names
    single_word_blacklist = {
        "golden", "super", "oscar", "emmy", "grammy", "cannes", "sundance",
        "billboard", "variety", "vogue", "elle", "people", "time", "us",
        "new", "old", "big", "little", "young", "real", "true", "good", "bad"
    }
    all_keys = [k for k, _ in rows]
    single_word = [
        k for k in all_keys
        if "_" not in k and len(k) > 2 and k not in single_word_blacklist
    ]
    for short in single_word:
        for long_key in all_keys:
            if long_key == short:
                continue
            if long_key.startswith(short + "_"):
                canonical = long_key
                if canonical not in groups:
                    groups[canonical] = set()
                groups[canonical].add(short)

    # Strategy 4: hardcoded manual pairs for known multi-alias celebrities
    # Format: canonical_key -> [alias_keys]
    MANUAL_PAIRS = {
        "kanye_west": ["kanye", "ye"],
        "beyonce_knowles": ["beyonce", "beyonce_knowles_carter"],
        "adele_adkins": ["adele"],
        "donald_trump": ["donald_j_trump", "trump"],
        "jennifer_lopez": ["jlo", "j_lo"],
        "nicki_minaj": ["nicki"],
        "cardi_b": ["cardi"],
        "lizzo": ["melissa_jefferson"],
        "doja_cat": ["amala_dlamini"],
    }
    for canonical, aliases in MANUAL_PAIRS.items():
        # Only apply if canonical exists in the DB
        existing_keys = {k for k, _ in rows}
        if canonical not in existing_keys:
            continue
        valid_aliases = [a for a in aliases if a in existing_keys and a != canonical]
        if valid_aliases:
            if canonical not in groups:
                groups[canonical] = set()
            groups[canonical].update(valid_aliases)

    # Remove self-references and empty groups
    result = []
    for canonical, aliases in groups.items():
        aliases.discard(canonical)
        if aliases:
            result.append((canonical, sorted(aliases)))

    return result

def apply_merges(db_path: Path, merges: list):
    """
    For each (canonical, [aliases]) pair:
    - Set canonical_key on alias rows pointing to canonical
    - Merge temperature: canonical gets max(canonical_temp, alias_temp)
    - Set alias status to 'alias' so Jekyll can hide them from display
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Add canonical_key column if it doesn't exist yet
    try:
        c.execute("ALTER TABLE celebrities ADD COLUMN canonical_key TEXT DEFAULT NULL")
        conn.commit()
        print("  Added canonical_key column to celebrities table")
    except sqlite3.OperationalError:
        pass  # Column already exists

    merged_count = 0
    for canonical, aliases in merges:
        # Get canonical temperature
        c.execute("SELECT temperature FROM celebrities WHERE key = ?", (canonical,))
        row = c.fetchone()
        if not row:
            continue
        canonical_temp = row[0]

        for alias in aliases:
            c.execute("SELECT temperature FROM celebrities WHERE key = ?", (alias,))
            arow = c.fetchone()
            if not arow:
                continue
            alias_temp = arow[0]

            # Merge temperature into canonical (take max)
            new_temp = max(canonical_temp, alias_temp)
            if new_temp != canonical_temp:
                if not DRY_RUN:
                    c.execute(
                        "UPDATE celebrities SET temperature = ? WHERE key = ?",
                        (new_temp, canonical)
                    )
                canonical_temp = new_temp

            # Mark alias with canonical_key and status='alias'
            if not DRY_RUN:
                c.execute(
                    "UPDATE celebrities SET canonical_key = ?, status = 'alias' WHERE key = ?",
                    (canonical, alias)
                )
            merged_count += 1

    if not DRY_RUN:
        conn.commit()
    conn.close()
    return merged_count

def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description="TGR celebrity deduplication")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show", action="store_true", help="Just show duplicates, no changes")
    parser.add_argument("--path", default=".", help="Path to thegossroom repo root")
    args = parser.parse_args()

    DRY_RUN = args.dry_run or args.show
    base_dir = Path(args.path).resolve()
    db_path = base_dir / "_data" / "tgr.db"

    if not db_path.exists():
        print(f"❌ DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    # Check if canonical_key column exists yet
    cols = [r[1] for r in conn.execute("PRAGMA table_info(celebrities)").fetchall()]
    if "canonical_key" in cols:
        rows = conn.execute(
            "SELECT key, name FROM celebrities WHERE (canonical_key IS NULL OR canonical_key = '') AND status != 'alias'"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT key, name FROM celebrities"
        ).fetchall()
    conn.close()

    print(f"📊 Analysing {len(rows)} celebrities for duplicates...")
    merges = find_duplicates(rows)

    if not merges:
        print("✅ No duplicates found")
        return

    print(f"\n🔍 Found {len(merges)} merge groups ({sum(len(a) for _, a in merges)} aliases):\n")
    for canonical, aliases in sorted(merges, key=lambda x: len(x[1]), reverse=True)[:40]:
        print(f"  {canonical:30s} ← {', '.join(aliases)}")

    if len(merges) > 40:
        print(f"  ... and {len(merges) - 40} more")

    if args.show:
        return

    if DRY_RUN:
        print(f"\n🔍 DRY RUN: would merge {sum(len(a) for _, a in merges)} aliases")
        return

    confirm = input(f"\nApply {len(merges)} merges? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    merged = apply_merges(db_path, merges)
    print(f"\n✅ Merged {merged} alias records")
    print("   Aliases have canonical_key set and status='alias'")
    print("   Scraper should now check canonical_key before double-boosting")
    print("\nNext: update enhanced_gossip_scraper.py to skip alias rows when boosting")
    print("      (boost canonical instead if alias is detected)")

if __name__ == "__main__":
    main()
