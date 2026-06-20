#!/usr/bin/env python3
"""
TGR Migration Script - One-shot ninja fix
Does:
  1. Nukes all celebrities_backup_*.yml files (keeps latest 1 as safety net)
  2. Patches enhanced_gossip_scraper.py - removes backup creation, adds slug to frontmatter
  3. Patches bluesky_poster.py - fixes URL generation to use frontmatter slug
  4. Creates SQLite DB on Harold-ready schema (celebrities + posts + sources)
  5. Migrates celebrities.yml into SQLite
  6. Writes _data/celebrities_snapshot.json for Jekyll to read (replaces YAML)
  7. Adds score floor (min 2.0) and velocity field to all celebrity records
  8. Reports everything it did

Run from: ~/www/thegossroom/
Usage: python3 tgr_migrate.py [--dry-run]
"""

import sys
import os
import re
import json
import yaml
import shutil
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

DRY_RUN = False

def log(msg, emoji=""):
    print(f"{emoji} {msg}".strip())

def patch_file(path, description, old, new):
    """Surgical string replacement in a file."""
    content = path.read_text(encoding="utf-8")
    if old not in content:
        log(f"SKIP patch '{description}' - pattern not found in {path.name}", "⚠️")
        return False
    if DRY_RUN:
        log(f"DRY RUN: would patch '{description}' in {path.name}", "🔍")
        return True
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    log(f"Patched '{description}' in {path.name}", "✅")
    return True

# ---------------------------------------------------------------------------
# STEP 1 - Nuke backup files
# ---------------------------------------------------------------------------
def nuke_backups(data_dir):
    backups = sorted(data_dir.glob("celebrities_backup_*.yml"))
    if not backups:
        log("No backup files found", "ℹ️")
        return
    # Keep the most recent one as a safety net
    keep = backups[-1]
    to_delete = backups[:-1]
    log(f"Found {len(backups)} backup files. Keeping latest: {keep.name}", "📋")
    if DRY_RUN:
        log(f"DRY RUN: would delete {len(to_delete)} backup files", "🔍")
        return
    for f in to_delete:
        f.unlink()
    log(f"Deleted {len(to_delete)} backup files. Repo is now clean.", "🗑️")

# ---------------------------------------------------------------------------
# STEP 2 - Patch scraper: remove backup creation, add slug to frontmatter
# ---------------------------------------------------------------------------
def patch_scraper(scripts_dir):
    scraper = scripts_dir / "enhanced_gossip_scraper.py"
    if not scraper.exists():
        log(f"Scraper not found at {scraper}", "❌")
        return

    # Remove the backup creation block
    patch_file(
        scraper,
        "remove backup file creation",
        old="""            # Create backup
            celebrities_file = celebrities_dir / 'celebrities.yml'
            if celebrities_file.exists():
                backup_file = celebrities_dir / f'celebrities_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.yml'
                shutil.copy2(celebrities_file, backup_file)
                logger.info(f"📋 Created backup: {backup_file.name}")""",
        new="""            celebrities_file = celebrities_dir / 'celebrities.yml'
            # NOTE: Backups removed - Harold SQLite is the source of truth now"""
    )

    # Add slug to frontmatter in create_blog_post
    # The slug field is what bluesky_poster.py uses to build the correct URL
    patch_file(
        scraper,
        "add slug field to post frontmatter",
        old="""        front_matter = {
            'layout': 'post',
            'title': title,
            'date': pub_datetime.isoformat(),
            'source': source_name,
            'source_url': link,""",
        new="""        front_matter = {
            'layout': 'post',
            'title': title,
            'slug': slug,
            'date': pub_datetime.isoformat(),
            'source': source_name,
            'source_url': link,"""
    )

    # Also remove shutil import if backup removal made it unused
    # (safe to leave it, won't error either way)

# ---------------------------------------------------------------------------
# STEP 3 - Patch Bluesky poster: use frontmatter slug reliably
# ---------------------------------------------------------------------------
def patch_bluesky_poster(scripts_dir):
    poster = scripts_dir / "bluesky_poster.py"
    if not poster.exists():
        log(f"Bluesky poster not found at {poster}", "❌")
        return

    # Replace the URL generation method with a cleaner version
    old_method = '''    def generate_post_url(self, filename, frontmatter=None):
        """
        Generate Jekyll post URL from filename.

        Prefers frontmatter slug/permalink fields if available, since
        Jekyll may derive the URL from the post title rather than filename
        (especially when titles contain special characters or the filename
        was truncated to 50 chars during scraping).
        """
        # Prefer explicit permalink in frontmatter
        if frontmatter:
            if frontmatter.get('permalink'):
                perm = frontmatter['permalink'].strip('/')
                return f"{self.site_base_url}/{perm}/"
            if frontmatter.get('slug'):
                slug = frontmatter['slug'].strip()
                # Still need the date — fall through to extract it from filename

        if not filename.endswith('.md'):
            return self.site_base_url

        name_without_ext = filename[:-3]
        if len(name_without_ext) < 10:
            return self.site_base_url

        date_part = name_without_ext[:10]
        slug_part = name_without_ext[11:]

        try:
            year, month, day = date_part.split('-')

            # Use frontmatter slug if we have one but no explicit permalink
            if frontmatter and frontmatter.get('slug'):
                clean_slug = frontmatter['slug'].strip().strip('/')
            else:
                clean_slug = slug_part.rstrip('-').rstrip('_')
                clean_slug = re.sub(r'-+', '-', clean_slug)
                clean_slug = clean_slug.strip('-')

            if not clean_slug:
                clean_slug = "post"

            return f"{self.site_base_url}/{year}/{month}/{day}/{clean_slug}/"
        except Exception:
            return self.site_base_url'''

    new_method = '''    def generate_post_url(self, filename, frontmatter=None):
        """
        Generate Jekyll post URL from filename + frontmatter.

        Priority order:
          1. frontmatter['permalink'] - explicit override
          2. frontmatter['slug'] - written by scraper from clean_slug()
          3. filename slug - fallback only (may be truncated, use with caution)

        The scraper now writes slug: to every post frontmatter so option 2
        should always be available, making 404s from truncated filenames impossible.
        """
        if not filename.endswith('.md'):
            return self.site_base_url

        # Extract date from filename - always reliable
        name_without_ext = filename[:-3]
        if len(name_without_ext) < 10:
            return self.site_base_url

        date_part = name_without_ext[:10]
        try:
            year, month, day = date_part.split('-')
        except ValueError:
            return self.site_base_url

        # Prefer explicit permalink
        if frontmatter and frontmatter.get('permalink'):
            perm = str(frontmatter['permalink']).strip('/')
            return f"{self.site_base_url}/{perm}/"

        # Use frontmatter slug (written by scraper - matches Jekyll exactly)
        if frontmatter and frontmatter.get('slug'):
            clean_slug = str(frontmatter['slug']).strip().strip('/')
            if clean_slug:
                return f"{self.site_base_url}/{year}/{month}/{day}/{clean_slug}/"

        # Fallback: derive slug from filename (may be truncated - less reliable)
        slug_part = name_without_ext[11:]
        clean_slug = re.sub(r'-+', '-', slug_part).strip('-')
        if not clean_slug:
            clean_slug = "post"
        return f"{self.site_base_url}/{year}/{month}/{day}/{clean_slug}/"'''

    patch_file(poster, "fix URL generation to use frontmatter slug", old_method, new_method)

# ---------------------------------------------------------------------------
# STEP 4+5 - Create SQLite DB and migrate celebrities.yml into it
# ---------------------------------------------------------------------------
def create_sqlite_db(base_dir):
    """
    Create Harold-ready SQLite schema and migrate celebrities.yml into it.
    The DB lives at _data/tgr.db — Harold will write to this,
    Jekyll reads from _data/celebrities_snapshot.json (generated each build).
    """
    db_path = base_dir / "_data" / "tgr.db"
    celebrities_yml = base_dir / "_data" / "celebrities.yml"

    if DRY_RUN:
        log(f"DRY RUN: would create SQLite DB at {db_path}", "🔍")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Celebrities table
    c.execute("""
        CREATE TABLE IF NOT EXISTS celebrities (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'unknown',
            temperature REAL DEFAULT 2.0,
            score_floor REAL DEFAULT 2.0,
            velocity REAL DEFAULT 0.0,
            status TEXT DEFAULT 'cooling',
            recent_story_count INTEGER DEFAULT 0,
            mention_count_30d INTEGER DEFAULT 0,
            last_seen TEXT,
            last_temp_update TEXT,
            discovery_date TEXT,
            memorial INTEGER DEFAULT 0,
            auto_discovered INTEGER DEFAULT 0,
            search_terms TEXT,
            aliases TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Posts table
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            guid TEXT PRIMARY KEY,
            filename TEXT UNIQUE,
            title TEXT,
            slug TEXT,
            source TEXT,
            source_url TEXT,
            drama_score REAL DEFAULT 0,
            temperature REAL DEFAULT 0,
            primary_celebrity TEXT,
            entities TEXT,
            tags TEXT,
            published_at TEXT,
            bluesky_posted INTEGER DEFAULT 0,
            bluesky_posted_at TEXT,
            archived INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Sources table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            key TEXT PRIMARY KEY,
            name TEXT,
            url TEXT,
            category TEXT,
            reliability_weight REAL DEFAULT 1.0,
            last_fetched TEXT,
            error_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    # Redirects table (for old story URL preservation)
    c.execute("""
        CREATE TABLE IF NOT EXISTS redirects (
            old_slug TEXT PRIMARY KEY,
            new_url TEXT,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    log(f"Created SQLite DB at {db_path}", "🗄️")

    # Migrate celebrities.yml
    if not celebrities_yml.exists():
        log("No celebrities.yml found — skipping migration", "⚠️")
        conn.close()
        return

    with open(celebrities_yml, "r", encoding="utf-8") as f:
        celebrities = yaml.safe_load(f) or {}

    migrated = 0
    now = datetime.now().isoformat()

    for key, data in celebrities.items():
        if not isinstance(data, dict):
            continue

        # Apply score floor
        raw_temp = data.get("temperature", data.get("drama_score", 0))
        temperature = max(2.0, float(raw_temp))

        search_terms = json.dumps(data.get("search_terms", []))
        aliases = json.dumps(data.get("aliases", []))

        c.execute("""
            INSERT OR REPLACE INTO celebrities
            (key, name, category, temperature, score_floor, velocity, status,
             recent_story_count, last_temp_update, discovery_date, memorial,
             auto_discovered, search_terms, aliases, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            data.get("name", key),
            data.get("category", "unknown"),
            temperature,
            2.0,  # score floor
            data.get("velocity", 0.0),
            data.get("status", "cooling"),
            data.get("recent_story_count", 0),
            data.get("last_temp_update", now),
            data.get("discovery_date", now[:10]),
            1 if data.get("memorial") else 0,
            1 if data.get("auto_discovered") else 0,
            search_terms,
            aliases,
            now
        ))
        migrated += 1

    conn.commit()
    conn.close()
    log(f"Migrated {migrated} celebrities into SQLite", "✅")

# ---------------------------------------------------------------------------
# STEP 6 - Write celebrities_snapshot.json for Jekyll
# ---------------------------------------------------------------------------
def write_jekyll_snapshot(base_dir):
    """
    Generate _data/celebrities_snapshot.json from SQLite.
    Jekyll uses this instead of the raw YAML. Much faster to parse.
    """
    db_path = base_dir / "_data" / "tgr.db"
    snapshot_path = base_dir / "_data" / "celebrities_snapshot.json"

    if DRY_RUN:
        log("DRY RUN: would write celebrities_snapshot.json", "🔍")
        return

    if not db_path.exists():
        log("SQLite DB not found — skipping snapshot", "⚠️")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT key, name, category, temperature, velocity, status,
               recent_story_count, memorial, last_temp_update
        FROM celebrities
        ORDER BY temperature DESC
    """)

    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    snapshot = {
        "generated_at": datetime.now().isoformat(),
        "total": len(rows),
        "celebrities": rows
    }

    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    log(f"Wrote {len(rows)} celebrities to {snapshot_path.name}", "📸")

# ---------------------------------------------------------------------------
# STEP 7 - Apply score floor to existing celebrities.yml (in-place)
# ---------------------------------------------------------------------------
def apply_score_floor(data_dir):
    """
    Apply minimum score of 2.0 to all celebrities in celebrities.yml
    so nobody fully disappears. Also adds velocity: 0.0 if missing.
    """
    celebrities_yml = data_dir / "celebrities.yml"
    if not celebrities_yml.exists():
        return

    with open(celebrities_yml, "r", encoding="utf-8") as f:
        celebrities = yaml.safe_load(f) or {}

    changed = 0
    for key, data in celebrities.items():
        if not isinstance(data, dict):
            continue
        t = data.get("temperature", data.get("drama_score", 0))
        if t < 2.0:
            data["temperature"] = 2.0
            changed += 1
        if "velocity" not in data:
            data["velocity"] = 0.0
            changed += 1

    if DRY_RUN:
        log(f"DRY RUN: would apply score floor to {changed} fields", "🔍")
        return

    with open(celebrities_yml, "w", encoding="utf-8") as f:
        yaml.dump(celebrities, f, default_flow_style=False, allow_unicode=True)

    log(f"Applied score floor/velocity to {changed} fields in celebrities.yml", "✅")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description="TGR one-shot migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--path", default=".", help="Path to thegossroom repo root")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    base_dir = Path(args.path).resolve()

    if not (base_dir / "_config.yml").exists():
        log(f"No _config.yml found at {base_dir} — are you in the right directory?", "❌")
        sys.exit(1)

    data_dir = base_dir / "_data"
    scripts_dir = base_dir / "scripts"

    log("=" * 55)
    log(f"TGR Migration {'(DRY RUN)' if DRY_RUN else ''}", "🚀")
    log(f"Base: {base_dir}")
    log("=" * 55)

    log("Step 1: Nuking backup files", "🗑️")
    nuke_backups(data_dir)

    log("Step 2: Patching scraper", "🔧")
    patch_scraper(scripts_dir)

    log("Step 3: Patching Bluesky poster", "🐦")
    patch_bluesky_poster(scripts_dir)

    log("Step 4+5: Creating SQLite DB + migrating celebrities", "🗄️")
    create_sqlite_db(base_dir)

    log("Step 6: Writing Jekyll snapshot JSON", "📸")
    write_jekyll_snapshot(base_dir)

    log("Step 7: Applying score floor to celebrities.yml", "📊")
    apply_score_floor(data_dir)

    log("=" * 55)
    log("Migration complete!", "🎉")
    log("")
    log("Next steps:", "📋")
    log("  1. Run: python3 scripts/enhanced_gossip_scraper.py")
    log("     Verify no backup file created, slug in frontmatter")
    log("  2. SCP _data/tgr.db to Harold: ~/web/thegossroom/_data/")
    log("  3. Check _data/celebrities_snapshot.json looks correct")
    log("  4. Commit and push (git will be MUCH lighter now)")
    log("  5. Test a Bluesky URL manually before enabling cron")

if __name__ == "__main__":
    main()
