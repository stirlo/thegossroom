#!/usr/bin/env python3
"""
Harold Run - TGR Pipeline Orchestrator
Replaces run_all.py with a clean Harold-native cron-friendly runner.

Cron schedule on Harold:
  */15 * * * *  python3 harold_run.py --scrape     # every 15 min
  19 * * * *    python3 harold_run.py --post        # bluesky at :19
  0 3 * * 0     python3 harold_run.py --weekly      # sunday 3am
  0 4 1 * *     python3 harold_run.py --monthly     # 1st of month 4am

Usage:
  python3 harold_run.py --scrape     # scrape + score + sync snapshot
  python3 harold_run.py --post       # bluesky post
  python3 harold_run.py --weekly     # archive management + tag cleanup
  python3 harold_run.py --monthly    # deep clean + memorial check
  python3 harold_run.py --build      # jekyll build + cf deploy
  python3 harold_run.py --status     # health check
  python3 harold_run.py --full       # everything in order (manual use only)
"""

import subprocess
import sys
import time
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent.resolve()
SCRIPTS = BASE / "scripts"
DATA = BASE / "_data"
POSTS = BASE / "_posts"
LOG_FILE = BASE / "harold.log"
DB_PATH = DATA / "tgr.db"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {level}: {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# Script runner
# ---------------------------------------------------------------------------

def run(script_name, args=None, timeout=600):
    """Run a script in the scripts/ directory."""
    path = SCRIPTS / script_name
    if not path.exists():
        log(f"Script not found: {script_name}", "WARN")
        return False

    cmd = [sys.executable, str(path)] + (args or [])
    log(f"Running: {script_name} {' '.join(args or '')}")
    start = time.time()

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=str(BASE)
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            log(f"OK: {script_name} ({elapsed:.1f}s)")
            # Print last 3 lines of output for quick visibility
            lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
            for line in lines[-3:]:
                log(f"  {line}")
            return True
        else:
            log(f"FAIL: {script_name} ({elapsed:.1f}s)", "ERROR")
            for line in result.stderr.strip().splitlines()[-5:]:
                log(f"  {line}", "ERROR")
            return False

    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: {script_name} exceeded {timeout}s", "ERROR")
        return False
    except Exception as e:
        log(f"EXCEPTION: {script_name} - {e}", "ERROR")
        return False

# ---------------------------------------------------------------------------
# SQLite snapshot sync
# ---------------------------------------------------------------------------

def sync_snapshot():
    """Regenerate celebrities_snapshot.json from SQLite after scraper runs."""
    if not DB_PATH.exists():
        log("DB not found, skipping snapshot sync", "WARN")
        return False

    try:
        import json
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT key, name, category, temperature, velocity, status,
                   recent_story_count, memorial, last_temp_update, canonical_key
            FROM celebrities
            WHERE (canonical_key IS NULL OR canonical_key = '')
              AND status != 'alias'
            ORDER BY temperature DESC
        """).fetchall()
        conn.close()

        snapshot = {
            "generated_at": datetime.now().isoformat(),
            "total": len(rows),
            "celebrities": [dict(r) for r in rows]
        }

        out = DATA / "celebrities_snapshot.json"
        with open(out, "w") as f:
            json.dump(snapshot, f, indent=2)

        log(f"Snapshot synced: {len(rows)} celebrities")
        return True
    except Exception as e:
        log(f"Snapshot sync failed: {e}", "ERROR")
        return False

# ---------------------------------------------------------------------------
# Jekyll build + CF deploy
# ---------------------------------------------------------------------------

def build_and_deploy():
    """Build Jekyll and push to Cloudflare Pages via Direct Upload API."""
    import os

    log("Building Jekyll...")
    result = subprocess.run(
        ["bundle", "exec", "jekyll", "build", "--incremental"],
        cwd=str(BASE), capture_output=True, text=True, timeout=300
    )

    if result.returncode != 0:
        log(f"Jekyll build failed: {result.stderr[-500:]}", "ERROR")
        return False

    log("Jekyll build OK")

    # Cloudflare Pages Direct Upload
    cf_token = os.getenv("CF_API_TOKEN")
    cf_account = os.getenv("CF_ACCOUNT_ID")
    cf_project = os.getenv("CF_PROJECT_NAME", "thegossroom")

    if not cf_token or not cf_account:
        log("CF credentials not set — skipping deploy", "WARN")
        return True  # Build succeeded, deploy skipped

    log("Deploying to Cloudflare Pages...")

    deploy_result = subprocess.run([
        "npx", "wrangler", "pages", "deploy", "_site",
        "--project-name", cf_project,
        "--commit-dirty=true"
    ],
        cwd=str(BASE),
        capture_output=True, text=True, timeout=300,
        env={**os.environ, "CLOUDFLARE_API_TOKEN": cf_token, "CLOUDFLARE_ACCOUNT_ID": cf_account}
    )

    if deploy_result.returncode == 0:
        log("CF Pages deploy OK")
        return True
    else:
        log(f"CF Pages deploy failed: {deploy_result.stderr[-300:]}", "ERROR")
        return False

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def status():
    """Quick health check of all moving parts."""
    log("=" * 50)
    log("TGR Harold Health Check")
    log("=" * 50)

    # DB
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        celeb_count = conn.execute("SELECT COUNT(*) FROM celebrities WHERE status != 'alias'").fetchone()[0]
        post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        top = conn.execute(
            "SELECT name, temperature FROM celebrities WHERE status != 'alias' ORDER BY temperature DESC LIMIT 3"
        ).fetchall()
        conn.close()
        log(f"DB: {celeb_count} celebrities, {post_count} posts tracked")
        log(f"Hottest: {', '.join(f'{n} ({t:.0f}°)' for n, t in top)}")
    else:
        log("DB: NOT FOUND", "WARN")

    # Posts dir
    post_files = list(POSTS.glob("*.md"))
    today = datetime.now().strftime("%Y-%m-%d")
    today_posts = [p for p in post_files if p.name.startswith(today)]
    log(f"Posts: {len(post_files)} total, {len(today_posts)} today")

    # Scripts
    required = [
        "enhanced_gossip_scraper.py",
        "bluesky_poster.py",
        "manage_archive.py",
    ]
    for s in required:
        exists = (SCRIPTS / s).exists()
        log(f"Script {s}: {'OK' if exists else 'MISSING'}", "INFO" if exists else "ERROR")

    # Last log entry
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text().splitlines()
        log(f"Last log: {lines[-1] if lines else 'empty'}")

    log("=" * 50)

# ---------------------------------------------------------------------------
# Pipeline modes
# ---------------------------------------------------------------------------

def pipeline_scrape():
    """15-min scrape cycle."""
    log("--- SCRAPE ---")
    ok = run("enhanced_gossip_scraper.py")
    if ok:
        sync_snapshot()
    return ok

def pipeline_post():
    """Bluesky post cycle."""
    log("--- BLUESKY POST ---")
    return run("bluesky_poster_enhanced.py")

def pipeline_weekly():
    """Weekly maintenance."""
    log("--- WEEKLY ---")
    run("tag_cleanup.py", ["cleanup"])
    run("manage_archive.py", ["--mode", "weekly"])
    sync_snapshot()

def pipeline_monthly():
    """Monthly deep clean."""
    log("--- MONTHLY ---")
    run("mega_archive.py", ["--days", "30", "--min-posts", "3"])
    run("manage_archive.py", ["--mode", "monthly"])
    run("memorial_cleanup.py", ["cleanup"])
    run("memorial_cleanup.py", ["update-expiry"])
    sync_snapshot()

def pipeline_full():
    """Full pipeline — manual use only."""
    log("--- FULL PIPELINE ---")
    pipeline_scrape()
    time.sleep(3)
    pipeline_post()
    time.sleep(3)
    build_and_deploy()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TGR Harold Orchestrator")
    parser.add_argument("--scrape", action="store_true")
    parser.add_argument("--post", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--monthly", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.scrape:
        pipeline_scrape()
    elif args.post:
        pipeline_post()
    elif args.build:
        build_and_deploy()
    elif args.weekly:
        pipeline_weekly()
    elif args.monthly:
        pipeline_monthly()
    elif args.full:
        pipeline_full()
    elif args.status:
        status()
    else:
        status()
        print("\nUsage: python3 harold_run.py [--scrape|--post|--build|--weekly|--monthly|--full|--status]")

if __name__ == "__main__":
    main()
