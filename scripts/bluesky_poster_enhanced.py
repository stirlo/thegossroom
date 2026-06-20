#!/usr/bin/env python3
"""
Bluesky Poster (RSS-dedup edition)
Uses Bluesky's own RSS feed to prevent double-posting.
URL generation uses frontmatter slug field (written by scraper) — no more 404s.
"""

import requests
import yaml
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

SITE_BASE = "https://thegossroom.com"
BSKY_API  = "https://bsky.social/xrpc"
# Your Bluesky RSS — update DID if handle changes
BSKY_RSS  = "https://bsky.app/profile/did:plc:gx7eych32oavyzd2sydcjqki/rss"


class BlueskyPoster:
    def __init__(self):
        self.handle   = os.getenv("BLUESKY_HANDLE")
        self.password = os.getenv("BLUESKY_PASSWORD")
        self.session  = None
        self.base     = Path.cwd()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def authenticate(self):
        try:
            r = requests.post(
                f"{BSKY_API}/com.atproto.server.createSession",
                json={"identifier": self.handle, "password": self.password},
                timeout=30
            )
            if r.status_code == 200:
                self.session = r.json()
                logger.info("Authenticated with Bluesky")
                return True
            logger.error(f"Auth failed: {r.status_code}")
        except Exception as e:
            logger.error(f"Auth error: {e}")
        return False

    # ------------------------------------------------------------------
    # URL generation — uses frontmatter slug, falls back to filename
    # ------------------------------------------------------------------

    def post_url(self, filename: str, frontmatter: dict) -> str | None:
        """
        Build the canonical post URL.
        Priority:
          1. frontmatter['permalink']
          2. frontmatter['slug']  ← scraper writes this now, always reliable
          3. slug derived from filename (may be truncated — last resort)
        """
        if not filename.endswith(".md"):
            return None

        stem = filename[:-3]
        if len(stem) < 11:
            return None

        date_str = stem[:10]
        try:
            year, month, day = date_str.split("-")
        except ValueError:
            return None

        # 1. Explicit permalink
        if frontmatter.get("permalink"):
            perm = str(frontmatter["permalink"]).strip("/")
            return f"{SITE_BASE}/{perm}/"

        # 2. Frontmatter slug (written by enhanced_gossip_scraper.py)
        if frontmatter.get("slug"):
            slug = str(frontmatter["slug"]).strip().strip("/")
            if slug:
                return f"{SITE_BASE}/{year}/{month}/{day}/{slug}/"

        # 3. Filename fallback (truncated at 50 chars — may 404 on long titles)
        slug = re.sub(r"-+", "-", stem[11:]).strip("-")
        if slug:
            return f"{SITE_BASE}/{year}/{month}/{day}/{slug}/"

        return None

    # ------------------------------------------------------------------
    # Duplicate detection via Bluesky RSS
    # ------------------------------------------------------------------

    def already_posted_urls(self) -> set:
        try:
            r = requests.get(BSKY_RSS, timeout=15)
            if r.status_code != 200:
                return set()
            root = ET.fromstring(r.content)
            urls = set()
            for item in root.findall(".//item"):
                desc = item.find("description")
                if desc is not None and desc.text:
                    urls.update(re.findall(rf"{re.escape(SITE_BASE)}/[^\s\"<]+", desc.text))
            logger.info(f"RSS dedup: {len(urls)} already-posted URLs found")
            return urls
        except Exception as e:
            logger.warning(f"RSS dedup failed ({e}), proceeding without")
            return set()

    # ------------------------------------------------------------------
    # Validate URL
    # ------------------------------------------------------------------

    def url_ok(self, url: str) -> bool:
        try:
            r = requests.get(url, timeout=10, allow_redirects=True)
            if r.status_code >= 400:
                return False
            # Detect soft-404 (GitHub Pages / CF Pages style)
            if r.url.rstrip("/") == SITE_BASE.rstrip("/"):
                return False
            body = r.text[:2000].lower()
            for marker in ("page not found", "404", "doesn't exist", "not found"):
                if marker in body:
                    return False
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Find best unposted article
    # ------------------------------------------------------------------

    def best_candidate(self) -> dict | None:
        posted = self.already_posted_urls()
        posts_dir = self.base / "_posts"
        if not posts_dir.exists():
            return None

        candidates = []

        for f in posts_dir.glob("*.md"):
            if "recovered" in f.name:
                continue

            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue

            if not content.startswith("---"):
                continue

            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                continue

            if not fm.get("title"):
                continue

            temp = fm.get("temperature", fm.get("drama_score", 0))
            if temp < 25:
                continue

            url = self.post_url(f.name, fm)
            if not url:
                continue

            if url in posted:
                continue

            if not self.url_ok(url):
                logger.warning(f"Bad URL skipped: {url}")
                continue

            candidates.append({
                "filename": f.name,
                "title":    fm["title"],
                "temp":     temp,
                "celebrity": fm.get("primary_celebrity", ""),
                "tags":     fm.get("tags", []),
                "url":      url,
            })

        if not candidates:
            return None

        best = max(candidates, key=lambda x: x["temp"])
        logger.info(f"Selected: {best['title'][:60]} ({best['temp']}°)")
        return best

    # ------------------------------------------------------------------
    # Compose post text
    # ------------------------------------------------------------------

    def compose(self, article: dict) -> str:
        temp      = article["temp"]
        title     = article["title"]
        url       = article["url"]
        celebrity = article["celebrity"].replace("_", " ").title() if article["celebrity"] else ""
        tags      = article.get("tags", [])

        badge = "🔥🔥🔥 EXPLOSIVE" if temp >= 40 else ("🔥🔥 HOT" if temp >= 30 else "🔥 HEATING UP")

        hashtags = "#gossip"
        for tag in tags[:3]:
            clean = re.sub(r"[^a-z0-9]", "", tag.lower())
            if len(clean) > 2 and clean != "gossip":
                hashtags += f" #{clean}"

        body = f"{badge}\n\n"
        if celebrity:
            body += f"🎯 {celebrity}\n"
        body += f"🌡️ {temp}°\n\n"

        space = 300 - len(body) - len(url) - len(hashtags) - 10
        if len(title) > space:
            title = title[:space - 3] + "..."

        body += f"📰 {title}\n\n{url}\n\n{hashtags}"
        return body[:300]

    # ------------------------------------------------------------------
    # Post
    # ------------------------------------------------------------------

    def post(self, text: str) -> bool:
        if not self.session:
            return False

        facets = []
        for m in re.finditer(r"https?://\S+", text):
            facets.append({
                "index": {
                    "byteStart": len(text[:m.start()].encode()),
                    "byteEnd":   len(text[:m.end()].encode())
                },
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}]
            })

        payload = {
            "repo": self.session["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "facets": facets
            }
        }

        try:
            r = requests.post(
                f"{BSKY_API}/com.atproto.repo.createRecord",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.session['accessJwt']}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            if r.status_code == 200:
                logger.info("Posted successfully")
                return True
            logger.error(f"Post failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            logger.error(f"Post error: {e}")
        return False

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self):
        logger.info("Bluesky poster starting...")

        if not self.handle or not self.password:
            logger.error("BLUESKY_HANDLE / BLUESKY_PASSWORD not set")
            print("posts_made=false")
            return

        if not self.authenticate():
            print("posts_made=false")
            return

        article = self.best_candidate()
        if not article:
            logger.info("No eligible articles")
            print("posts_made=false")
            return

        text = self.compose(article)
        logger.info(f"Posting: {article['title'][:60]}...")

        if self.post(text):
            print("posts_made=true")
        else:
            print("posts_made=false")


if __name__ == "__main__":
    BlueskyPoster().run()
