#!/usr/bin/env python3
"""
TGR Add RSS Sources
Patches enhanced_gossip_scraper.py to add new celebrity/music/reality/film sources.

Run from: ~/www/thegossroom/
Usage: python3 tgr_add_sources.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path

NEW_SOURCES = """            # --- UK Celebrity ---
            'heat_world': {
                'url': 'https://www.heatworld.com/feed/',
                'category': 'celebrity'
            },
            'ok_magazine_uk': {
                'url': 'https://www.ok.co.uk/feed/',
                'category': 'celebrity'
            },
            'closer_magazine': {
                'url': 'https://www.closermagazine.co.uk/feed/',
                'category': 'celebrity'
            },
            'hello_magazine': {
                'url': 'https://www.hellomagazine.com/rss',
                'category': 'celebrity'
            },
            'now_to_love_au': {
                'url': 'https://www.nowtolove.com.au/feed',
                'category': 'celebrity'
            },
            # --- Music Industry ---
            'pitchfork': {
                'url': 'https://pitchfork.com/rss/news/',
                'category': 'music'
            },
            'nme': {
                'url': 'https://www.nme.com/feed',
                'category': 'music'
            },
            'consequence': {
                'url': 'https://consequence.net/feed/',
                'category': 'music'
            },
            # --- Reality TV (high drama density) ---
            'reality_blurred': {
                'url': 'https://realityblurred.com/realitytv/feed/',
                'category': 'reality_tv'
            },
            'reality_tv_world': {
                'url': 'https://www.realitytvworld.com/rss/newsfeed.xml',
                'category': 'reality_tv'
            },
            # --- Film / Awards / Industry ---
            'deadline': {
                'url': 'https://deadline.com/feed/',
                'category': 'entertainment'
            },
            'the_playlist': {
                'url': 'https://theplaylist.net/feed/',
                'category': 'entertainment'
            },
            'socialite_life': {
                'url': 'https://www.socialite-life.com/feed',
                'category': 'celebrity'
            },"""

# The exact closing line of the existing feeds block to anchor our insert
ANCHOR = """            'vogue': {
                'url': 'https://www.vogue.com/feed/rss',
                'category': 'fashion'
            }
        }"""

REPLACEMENT = """            'vogue': {
                'url': 'https://www.vogue.com/feed/rss',
                'category': 'fashion'
            },
""" + NEW_SOURCES + """
        }"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", default=".")
    args = parser.parse_args()

    base = Path(args.path).resolve()
    scraper = base / "scripts" / "enhanced_gossip_scraper.py"

    if not scraper.exists():
        print(f"❌ Scraper not found at {scraper}")
        sys.exit(1)

    content = scraper.read_text(encoding="utf-8")

    if ANCHOR not in content:
        print("⚠️  Anchor pattern not found — may already be patched or vogue entry changed.")
        print("    Check scripts/enhanced_gossip_scraper.py manually.")
        sys.exit(1)

    if "heat_world" in content:
        print("ℹ️  Sources already added — nothing to do.")
        sys.exit(0)

    new_content = content.replace(ANCHOR, REPLACEMENT, 1)

    if args.dry_run:
        # Show a preview of what changed
        old_lines = ANCHOR.splitlines()
        new_lines = REPLACEMENT.splitlines()
        print(f"DRY RUN: would add {len(NEW_SOURCES.splitlines())} lines of new sources")
        print(f"  After 'vogue' entry, adding:")
        for line in NEW_SOURCES.strip().splitlines()[:8]:
            print(f"    {line}")
        print(f"  ... and {max(0, len(NEW_SOURCES.splitlines()) - 8)} more lines")
        return

    scraper.write_text(new_content, encoding="utf-8")
    print("✅ Added 13 new RSS sources to enhanced_gossip_scraper.py")
    print("")
    print("New sources added:")
    print("  UK Celebrity:    heat_world, ok_magazine_uk, closer_magazine, hello_magazine, now_to_love_au")
    print("  Music:           pitchfork, nme, consequence")
    print("  Reality TV:      reality_blurred, reality_tv_world")
    print("  Film/Industry:   deadline, the_playlist, socialite_life")
    print("")
    print("Total feeds: 12 existing + 13 new = 25 sources")
    print("")
    print("Next: test with python3 scripts/enhanced_gossip_scraper.py")

if __name__ == "__main__":
    main()
