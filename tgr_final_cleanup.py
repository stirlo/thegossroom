#!/usr/bin/env python3
"""
TGR Final Cleanup - Everything in one shot.

Does:
  1. Fix _config.yml email (remove angle brackets)
  2. Update harold_run.py to use bluesky_poster_enhanced.py
  3. Patch manage_archive.py to read celebrities_snapshot.json not raw YAML
  4. Create mega_archive.py - consolidates old posts per celebrity into one rich post
  5. Add _redirects generation to harold_run.py (CF Pages redirect map)
  6. Write .gitignore additions (tgr.db, harold.log, _retired/)
  7. Fix _config.yml to not silently drop pre-2024 posts (remove bad exclude)

Run from: ~/www/thegossroom/
Usage: python3 tgr_final_cleanup.py [--dry-run]
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

DRY = False

def log(msg, emoji=""):
    print(f"{emoji} {msg}".strip())

def write(path, content, description):
    if DRY:
        log(f"DRY: would write {path}", "🔍")
        return
    Path(path).write_text(content, encoding="utf-8")
    log(f"Wrote {description}: {path}", "✅")

def patch(path, description, old, new):
    p = Path(path)
    if not p.exists():
        log(f"SKIP {description} - file not found: {path}", "⚠️")
        return False
    content = p.read_text(encoding="utf-8")
    if old not in content:
        log(f"SKIP {description} - pattern not found (already patched?)", "⚠️")
        return False
    if DRY:
        log(f"DRY: would patch '{description}' in {p.name}", "🔍")
        return True
    p.write_text(content.replace(old, new, 1), encoding="utf-8")
    log(f"Patched '{description}' in {p.name}", "✅")
    return True

# ---------------------------------------------------------------------------
# 1. Fix _config.yml email
# ---------------------------------------------------------------------------
def fix_config(base):
    patch(
        base / "_config.yml",
        "fix email angle brackets",
        old="email: <mailto:s@oursquadis.top>",
        new="email: s@oursquadis.top"
    )
    # Remove the silent pre-2024 post exclusion
    patch(
        base / "_config.yml",
        "remove silent pre-2024 post exclusion",
        old='  - "_posts/202[0-3]-*"     # Exclude posts older than 2024\n',
        new=""
    )

# ---------------------------------------------------------------------------
# 2. Update harold_run.py to use bluesky_poster_enhanced.py
# ---------------------------------------------------------------------------
def fix_harold_run(base):
    patch(
        base / "harold_run.py",
        "use bluesky_poster_enhanced as the one true poster",
        old='    return run("bluesky_poster.py")',
        new='    return run("bluesky_poster_enhanced.py")'
    )

# ---------------------------------------------------------------------------
# 3. Patch manage_archive.py to read snapshot JSON not raw YAML
# ---------------------------------------------------------------------------
def fix_manage_archive(base):
    patch(
        base / "scripts" / "manage_archive.py",
        "read celebrities from snapshot JSON not raw YAML",
        old="""    def load_celebrities(self):
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}""",
        new="""    def load_celebrities(self):
        \"\"\"Load from SQLite snapshot JSON (Harold source of truth).\"\"\"
        snapshot = self.base_path / '_data' / 'celebrities_snapshot.json'
        if snapshot.exists():
            try:
                import json as _json
                data = _json.loads(snapshot.read_text())
                # Convert list to dict keyed by 'key' field
                return {c['key']: c for c in data.get('celebrities', [])}
            except Exception:
                pass
        # Fallback to YAML for local dev without Harold DB
        yml = self.base_path / '_data' / 'celebrities.yml'
        try:
            return yaml.safe_load(yml.read_text()) or {}
        except FileNotFoundError:
            return {}"""
    )

# ---------------------------------------------------------------------------
# 4. Write mega_archive.py
# ---------------------------------------------------------------------------
MEGA_ARCHIVE_PY = '''#!/usr/bin/env python3
"""
TGR Mega Archive - Consolidates old posts per celebrity into rich summary posts.

For each celebrity with posts older than ARCHIVE_DAYS:
  - Groups posts by celebrity
  - Creates one "mega post" summarising all stories
  - Writes 301 redirects from each old post slug to the mega post
  - Moves old posts to _archive/

This keeps the site fast (fewer active posts), preserves SEO (no 404s),
and creates richer content (one well-linked page per celebrity arc).

Usage:
  python3 scripts/mega_archive.py --dry-run    # preview
  python3 scripts/mega_archive.py              # run
  python3 scripts/mega_archive.py --days 14   # custom threshold
"""

import re
import yaml
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SITE_BASE = "https://thegossroom.com"

class MegaArchiver:
    def __init__(self, dry_run=False, archive_days=30, min_posts=3):
        self.dry    = dry_run
        self.days   = archive_days
        self.min    = min_posts          # min posts before consolidating
        self.base   = Path(".")
        self.posts  = self.base / "_posts"
        self.archive= self.base / "_archive"
        self.data   = self.base / "_data"
        self.archive.mkdir(exist_ok=True)

        # Load existing redirects
        self.redirects_file = self.base / "_redirects"
        self.redirects = self._load_redirects()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_redirects(self):
        if self.redirects_file.exists():
            lines = self.redirects_file.read_text().splitlines()
            return [l for l in lines if l.strip() and not l.startswith("#")]
        return []

    def _save_redirects(self):
        header = "# Auto-generated by mega_archive.py\\n# DO NOT EDIT MANUALLY\\n"
        content = header + "\\n".join(sorted(set(self.redirects))) + "\\n"
        if not self.dry:
            self.redirects_file.write_text(content)
        print(f"  Redirects: {len(self.redirects)} rules")

    def _post_url(self, filename):
        stem = filename.replace(".md", "")
        if len(stem) < 11:
            return None
        try:
            y, m, d = stem[:10].split("-")
            slug = re.sub(r"-+", "-", stem[11:]).strip("-")
            return f"{SITE_BASE}/{y}/{m}/{d}/{slug}/"
        except Exception:
            return None

    def _parse(self, path):
        try:
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None, None
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None, None
            fm = yaml.safe_load(parts[1]) or {}
            return fm, parts[2].strip()
        except Exception:
            return None, None

    def _date_from_file(self, path):
        try:
            return datetime.strptime(path.name[:10], "%Y-%m-%d")
        except Exception:
            return datetime.now()

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------

    def find_archivable_posts(self):
        """Find posts older than threshold, grouped by primary celebrity."""
        cutoff = datetime.now() - timedelta(days=self.days)
        groups = defaultdict(list)

        for f in self.posts.glob("*.md"):
            date = self._date_from_file(f)
            if date >= cutoff:
                continue  # Too recent

            fm, body = self._parse(f)
            if not fm:
                continue

            celeb = fm.get("primary_celebrity", "").strip()
            if not celeb:
                celeb = "_uncategorised"

            groups[celeb].append({
                "file": f,
                "fm": fm,
                "body": body,
                "date": date,
                "url": self._post_url(f.name),
            })

        # Only consolidate celebrities with enough old posts
        return {k: v for k, v in groups.items() if len(v) >= self.min}

    def create_mega_post(self, celebrity, posts):
        """Create one rich summary post for a celebrity\'s old stories."""
        posts_sorted = sorted(posts, key=lambda x: x["date"], reverse=True)
        newest = posts_sorted[0]["date"]
        oldest = posts_sorted[-1]["date"]

        celeb_display = celebrity.replace("_", " ").title()
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = f"{celebrity}-archive"
        filename = f"{date_str}-{slug}.md"
        mega_url = self._post_url(filename)

        # Build rich body
        sections = []
        for p in posts_sorted:
            title = p["fm"].get("title", "Untitled")
            src_url = p["fm"].get("source_url", "")
            src = p["fm"].get("source", "")
            date_fmt = p["date"].strftime("%B %d, %Y")
            body_excerpt = (p["body"] or "")[:300].strip()
            if len(p["body"] or "") > 300:
                body_excerpt += "..."

            section = f"### {title}\\n"
            section += f"*{date_fmt}*"
            if src:
                section += f" — [{src}]({src_url})" if src_url else f" — {src}"
            section += f"\\n\\n{body_excerpt}\\n"
            sections.append(section)

        # Aggregate scores
        avg_temp = sum(p["fm"].get("temperature", 0) for p in posts) / len(posts)
        max_drama = max(p["fm"].get("drama_score", 0) for p in posts)
        all_tags = list({t for p in posts for t in p["fm"].get("tags", [])})

        fm_out = {
            "layout": "post",
            "title": f"{celeb_display}: Complete Story Archive",
            "slug": slug,
            "date": datetime.now().isoformat(),
            "primary_celebrity": celebrity,
            "is_mega_archive": True,
            "story_count": len(posts),
            "date_range_start": oldest.strftime("%Y-%m-%d"),
            "date_range_end": newest.strftime("%Y-%m-%d"),
            "temperature": round(avg_temp),
            "drama_score": max_drama,
            "tags": all_tags[:10],
            "categories": ["archive", "gossip"],
            "description": (
                f"Complete archive of {len(posts)} stories about {celeb_display} "
                f"from {oldest.strftime('%B %Y')} to {newest.strftime('%B %Y')}."
            ),
        }

        body_out = f"""## {celeb_display} — {len(posts)} Stories

*Covering {oldest.strftime('%B %Y')} through {newest.strftime('%B %Y')}*

This archive consolidates all stories about {celeb_display} into one navigable page.

---

""" + "\\n\\n---\\n\\n".join(sections)

        content = f"---\\n{yaml.dump(fm_out, default_flow_style=False)}---\\n\\n{body_out}\\n"
        return filename, content, mega_url

    def run(self):
        print(f"🗂️  Mega Archive {'(DRY RUN)' if self.dry else ''}")
        print(f"   Threshold: {self.days} days, min {self.min} posts to consolidate")

        groups = self.find_archivable_posts()

        if not groups:
            print("   Nothing to consolidate.")
            return

        total_old = sum(len(v) for v in groups.values())
        print(f"   Found {len(groups)} celebrities, {total_old} posts to consolidate\\n")

        created = 0
        archived = 0
        redirected = 0

        for celeb, posts in sorted(groups.items()):
            print(f"  📦 {celeb.replace('_',' ').title()} — {len(posts)} posts")

            filename, content, mega_url = self.create_mega_post(celeb, posts)

            # Write mega post
            mega_path = self.posts / filename
            if not self.dry:
                mega_path.write_text(content, encoding="utf-8")
            print(f"     → Mega post: {filename}")
            created += 1

            # Archive old posts + write redirects
            for p in posts:
                old_url = p["url"]
                if old_url and mega_url:
                    redirect_line = f"{old_url.replace(SITE_BASE, '')} {mega_url.replace(SITE_BASE, '')} 301"
                    self.redirects.append(redirect_line)
                    redirected += 1

                archive_path = self.archive / p["file"].name
                if not self.dry:
                    shutil.move(str(p["file"]), str(archive_path))
                archived += 1

        self._save_redirects()

        print(f"\\n✅ Done:")
        print(f"   {created} mega posts created")
        print(f"   {archived} old posts archived")
        print(f"   {redirected} redirects written to _redirects")
        if not self.dry:
            print(f"\\n   Commit _redirects and _posts/ then push.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--min-posts", type=int, default=3)
    args = parser.parse_args()
    MegaArchiver(dry_run=args.dry_run, archive_days=args.days, min_posts=args.min_posts).run()
'''

def write_mega_archive(base):
    out = base / "scripts" / "mega_archive.py"
    if DRY:
        log(f"DRY: would write mega_archive.py", "🔍")
        return
    out.write_text(MEGA_ARCHIVE_PY, encoding="utf-8")
    log("Wrote scripts/mega_archive.py", "✅")

# ---------------------------------------------------------------------------
# 5. Update harold_run.py to call mega_archive in monthly pipeline
# ---------------------------------------------------------------------------
def fix_harold_run_monthly(base):
    patch(
        base / "harold_run.py",
        "add mega_archive to monthly pipeline",
        old="""def pipeline_monthly():
    \"\"\"Monthly deep clean.\"\"\"
    log("--- MONTHLY ---")
    run("manage_archive.py", ["--mode", "monthly"])
    run("memorial_cleanup.py", ["cleanup"])
    run("memorial_cleanup.py", ["update-expiry"])
    sync_snapshot()""",
        new="""def pipeline_monthly():
    \"\"\"Monthly deep clean.\"\"\"
    log("--- MONTHLY ---")
    run("mega_archive.py", ["--days", "30", "--min-posts", "3"])
    run("manage_archive.py", ["--mode", "monthly"])
    run("memorial_cleanup.py", ["cleanup"])
    run("memorial_cleanup.py", ["update-expiry"])
    sync_snapshot()"""
    )

# ---------------------------------------------------------------------------
# 6. Update .gitignore
# ---------------------------------------------------------------------------
GITIGNORE_ADDITIONS = """
# Harold SQLite DB - lives on Harold, not in git
_data/tgr.db

# Harold log
harold.log
automation.log

# Retired scripts - kept locally, not needed in repo
scripts/_retired/

# Jekyll build output
_site/

# Python
__pycache__/
*.pyc
*.pyo

# Archive dirs - large, not needed in git
_archive/
_cold_storage/

# Cloudflare wrangler
.wrangler/
"""

def fix_gitignore(base):
    gi = base / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    additions = []
    for line in GITIGNORE_ADDITIONS.strip().splitlines():
        if line and line not in existing:
            additions.append(line)
    if not additions:
        log(".gitignore already up to date", "ℹ️")
        return
    if DRY:
        log(f"DRY: would add {len(additions)} lines to .gitignore", "🔍")
        return
    with open(gi, "a") as f:
        f.write("\n# --- Added by tgr_final_cleanup.py ---\n")
        f.write("\n".join(additions) + "\n")
    log(f"Updated .gitignore (+{len(additions)} lines)", "✅")

# ---------------------------------------------------------------------------
# 7. Write a clean README for the scripts/ dir
# ---------------------------------------------------------------------------
SCRIPTS_README = """# TGR Scripts

Harold-native pipeline for The Gossip Room.

## Active scripts

| Script | Purpose | Frequency |
|--------|---------|-----------|
| `enhanced_gossip_scraper.py` | Scrape RSS feeds, score posts, update SQLite | Every 15 min |
| `bluesky_poster_enhanced.py` | Post hottest story to Bluesky (RSS dedup) | Hourly at :19 |
| `mega_archive.py` | Consolidate old posts into rich archive pages | Monthly |
| `manage_archive.py` | Move old posts out of active _posts/ | Weekly/Monthly |
| `memorial_cleanup.py` | Handle deceased celebrity records | Monthly |
| `tag_cleanup.py` | Clean/merge tags across posts | Weekly |
| `drama_temperature_calculator.py` | Batch temperature recalc (legacy, rarely needed) | Manual only |

## Orchestrator

`harold_run.py` (in repo root) is the single entry point for Harold's cron.

```
*/15 * * * *  python3 harold_run.py --scrape
19 * * * *    python3 harold_run.py --post
0 3 * * 0     python3 harold_run.py --weekly
0 4 1 * *     python3 harold_run.py --monthly
```

## Retired scripts

Legacy emergency tools from the GitHub Actions era are in `_retired/`.
Do not restore them — they write directly to celebrities.yml which is
now a read-only Jekyll snapshot. Harold SQLite is the source of truth.
"""

def write_scripts_readme(base):
    out = base / "scripts" / "README.md"
    if DRY:
        log("DRY: would write scripts/README.md", "🔍")
        return
    out.write_text(SCRIPTS_README, encoding="utf-8")
    log("Wrote scripts/README.md", "✅")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global DRY
    parser = argparse.ArgumentParser(description="TGR final cleanup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", default=".")
    args = parser.parse_args()

    DRY = args.dry_run
    base = Path(args.path).resolve()

    if not (base / "_config.yml").exists():
        print(f"No _config.yml at {base} — wrong directory?")
        sys.exit(1)

    log("=" * 55)
    log(f"TGR Final Cleanup {'(DRY RUN)' if DRY else ''}", "✨")
    log("=" * 55)

    log("1. Fix _config.yml", "🔧")
    fix_config(base)

    log("2. Update harold_run.py → use enhanced poster", "🐦")
    fix_harold_run(base)

    log("3. Patch manage_archive.py → read snapshot JSON", "🗄️")
    fix_manage_archive(base)

    log("4. Write mega_archive.py", "📦")
    write_mega_archive(base)

    log("5. Add mega_archive to monthly pipeline", "📅")
    fix_harold_run_monthly(base)

    log("6. Update .gitignore", "📝")
    fix_gitignore(base)

    log("7. Write scripts/README.md", "📖")
    write_scripts_readme(base)

    log("=" * 55)
    log("Final cleanup complete!", "🎉")
    log("")
    log("Next steps:", "📋")
    log("  1. python3 tgr_retire_scripts.py          # retire legacy scripts")
    log("  2. cp bluesky_poster_enhanced.py scripts/ # deploy new poster")
    log("  3. cp harold_run.py ./                    # deploy orchestrator")
    log("  4. git add -A && git status               # review changes")
    log("  5. git commit -m 'feat: Harold-ready clean pipeline'")
    log("  6. git push")
    log("  7. rsync -av ~/www/thegossroom/ harold:~/web/thegossroom/")
    log("  8. ssh harold 'cd ~/web/thegossroom && bundle install'")
    log("  9. ssh harold 'python3 harold_run.py --status'")
    log(" 10. Set up cron on Harold (see scripts/README.md)")

if __name__ == "__main__":
    main()
