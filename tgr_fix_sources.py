#!/usr/bin/env python3
"""
TGR Fix Dead RSS Sources
Replaces the 3 dead/404 feeds and adds bonus UK/gossip sources discovered.

Dead feeds fixed:
  heat_world      → rss.onebauer.media (correct Bauer Media CDN URL)
  ok_magazine_uk  → okmagazine.com/rss (US OK! covers royals + celeb)
  socialite_life  → dead domain, replaced with theblast.com

Bonus sources added:
  mirror_3am, express_showbiz, entertainment_daily,
  female_first, the_sun_showbiz, life_and_style

Run from: ~/www/thegossroom/
Usage: python3 tgr_fix_sources.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path

FIXES = [
    # (description, old_string, new_string)
    (
        "fix heat_world URL to Bauer Media CDN",
        "'heat_world': {\n                'url': 'https://www.heatworld.com/feed/',",
        "'heat_world': {\n                'url': 'https://rss.onebauer.media/api/feed-heatworld',",
    ),
    (
        "fix ok_magazine_uk to US OK! Magazine",
        "'ok_magazine_uk': {\n                'url': 'https://www.ok.co.uk/feed/',",
        "'ok_magazine_uk': {\n                'url': 'https://okmagazine.com/rss',",
    ),
    (
        "replace dead socialite_life with The Blast",
        "'socialite_life': {\n                'url': 'https://www.socialite-life.com/feed',\n                'category': 'celebrity'\n            },",
        "'the_blast': {\n                'url': 'https://theblast.com/feed',\n                'category': 'celebrity'\n            },",
    ),
]

BONUS_SOURCES = """            # --- Bonus UK / Gossip sources ---
            'mirror_3am': {
                'url': 'https://www.mirror.co.uk/3am/?service=rss',
                'category': 'celebrity'
            },
            'express_showbiz': {
                'url': 'https://www.express.co.uk/posts/rss/79/celebrity-news',
                'category': 'celebrity'
            },
            'entertainment_daily': {
                'url': 'https://www.entertainmentdaily.co.uk/feed/',
                'category': 'celebrity'
            },
            'female_first': {
                'url': 'https://www.femalefirst.co.uk/celebrities/rss',
                'category': 'celebrity'
            },
            'the_sun_showbiz': {
                'url': 'https://www.thesun.co.uk/feed/',
                'category': 'celebrity'
            },
            'life_and_style': {
                'url': 'https://www.lifeandstylemag.com/?feed=posts',
                'category': 'celebrity'
            },"""

# Anchor — insert bonus sources just before the closing brace of rss_feeds
BONUS_ANCHOR = "            'the_blast': {\n                'url': 'https://theblast.com/feed',\n                'category': 'celebrity'\n            },\n        }"
BONUS_REPLACEMENT = "            'the_blast': {\n                'url': 'https://theblast.com/feed',\n                'category': 'celebrity'\n            },\n" + BONUS_SOURCES + "\n        }"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", default=".")
    args = parser.parse_args()

    base = Path(args.path).resolve()
    scraper = base / "scripts" / "enhanced_gossip_scraper.py"

    if not scraper.exists():
        print(f"❌ Scraper not found: {scraper}")
        sys.exit(1)

    content = scraper.read_text(encoding="utf-8")

    # Apply fixes
    for desc, old, new in FIXES:
        if old not in content:
            print(f"⚠️  SKIP '{desc}' — pattern not found (already patched?)")
            continue
        if args.dry_run:
            print(f"🔍 DRY: would fix '{desc}'")
        else:
            content = content.replace(old, new, 1)
            print(f"✅ Fixed: {desc}")

    # Add bonus sources
    if "mirror_3am" in content:
        print("ℹ️  Bonus sources already added")
    elif BONUS_ANCHOR not in content:
        print("⚠️  Bonus anchor not found — add manually after 'the_blast' entry")
    else:
        if args.dry_run:
            print(f"🔍 DRY: would add 6 bonus sources")
        else:
            content = content.replace(BONUS_ANCHOR, BONUS_REPLACEMENT, 1)
            print("✅ Added 6 bonus UK/gossip sources")

    if not args.dry_run:
        scraper.write_text(content, encoding="utf-8")
        print("")
        print("Feed summary:")
        print("  Fixed:  heat_world → Bauer CDN URL")
        print("          ok_magazine_uk → okmagazine.com")
        print("          socialite_life → the_blast")
        print("  Added:  mirror_3am, express_showbiz, entertainment_daily,")
        print("          female_first, the_sun_showbiz, life_and_style")
        print("")
        print("Total feeds: ~31 active sources")
        print("")
        print("Test with: python3 scripts/enhanced_gossip_scraper.py 2>&1 | grep -E 'Scraping|ERROR'")


if __name__ == "__main__":
    main()
