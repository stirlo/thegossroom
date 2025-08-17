#!/usr/bin/env python3
"""
RSS-Based Bluesky Poster - Zero File Dependencies
"""

import requests
import yaml
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class RSSBlueskyPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.site_base_url = "https://thegossroom.com"

        # RSS feed for duplicate checking
        self.rss_url = "https://bsky.app/profile/did:plc:gx7eych32oavyzd2sydcjqki/rss"

    def authenticate(self):
        """Authenticate with Bluesky"""
        auth_data = {"identifier": self.handle, "password": self.password}

        try:
            response = requests.post(f"{self.base_url}/com.atproto.server.createSession", 
                                   json=auth_data, timeout=30)
            if response.status_code == 200:
                self.session = response.json()
                logger.info("✅ Bluesky authenticated")
                return True
            else:
                logger.error(f"❌ Auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Auth error: {e}")
            return False

    def get_posted_urls_from_rss(self):
        """Get already posted URLs from RSS feed"""
        try:
            response = requests.get(self.rss_url, timeout=15)
            if response.status_code != 200:
                logger.warning("⚠️ RSS feed unavailable, proceeding without duplicate check")
                return set()

            root = ET.fromstring(response.content)
            posted_urls = set()

            # Extract URLs from RSS descriptions
            for item in root.findall('.//item'):
                description = item.find('description')
                if description is not None and description.text:
                    # Look for thegossroom.com URLs in the description
                    urls = re.findall(r'https://thegossroom\.com/[^\s]+', description.text)
                    posted_urls.update(urls)

            logger.info(f"📡 Found {len(posted_urls)} already posted URLs from RSS")
            return posted_urls

        except Exception as e:
            logger.warning(f"⚠️ RSS check failed: {e}, proceeding without duplicate check")
            return set()

    def validate_url(self, url):
        """Quick URL check"""
        try:
            response = requests.head(url, timeout=8, allow_redirects=True)
            return 200 <= response.status_code < 400
        except:
            return False

    def generate_url(self, filename):
        """Generate post URL"""
        if not filename.endswith('.md') or len(filename) < 14:
            return None

        date_part = filename[:10]
        slug_part = filename[11:-3]

        try:
            year, month, day = date_part.split('-')
            slug = re.sub(r'-+', '-', slug_part.strip('-'))
            return f"{self.site_base_url}/{year}/{month}/{day}/{slug}/"
        except:
            return None

    def parse_post(self, file_path):
        """Minimal post parsing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                return None

            frontmatter = yaml.safe_load(parts[1])
            return frontmatter if frontmatter else None

        except Exception as e:
            logger.debug(f"Parse failed {file_path.name}: {e}")
            return None

    def get_best_unposted(self):
        """Get the hottest unposted article using RSS check"""
        posted_urls = self.get_posted_urls_from_rss()
        posts_dir = Path('_posts')

        if not posts_dir.exists():
            return None

        candidates = []

        for post_file in posts_dir.glob('*.md'):
            # Skip recovered files
            if 'recovered' in post_file.name:
                continue

            # Generate URL first
            url = self.generate_url(post_file.name)
            if not url:
                continue

            # RSS DUPLICATE CHECK - This is the magic!
            if url in posted_urls:
                logger.debug(f"🛡️ RSS BLOCKED: {post_file.name}")
                continue

            # Parse frontmatter
            fm = self.parse_post(post_file)
            if not fm or not fm.get('title'):
                continue

            # Check temperature
            temp = fm.get('temperature', fm.get('drama_score', 0))
            if temp < 25:
                continue

            # Validate URL
            if not self.validate_url(url):
                logger.warning(f"⚠️ Bad URL: {post_file.name}")
                continue

            candidates.append({
                'filename': post_file.name,
                'title': fm['title'],
                'temperature': temp,
                'celebrity': fm.get('primary_celebrity', ''),
                'tags': fm.get('tags', []),
                'url': url
            })

        if not candidates:
            return None

        # Return hottest
        best = max(candidates, key=lambda x: x['temperature'])
        logger.info(f"🔥 Selected: {best['title'][:50]}... (Temp: {best['temperature']}°)")
        return best

    def create_post_text(self, article):
        """Create Bluesky post"""
        temp = article['temperature']
        title = article['title']
        url = article['url']
        celebrity = article['celebrity'].replace('_', ' ').title() if article['celebrity'] else ""

        # Temperature emoji
        if temp >= 40:
            emoji = "🔥🔥🔥 EXPLOSIVE"
        elif temp >= 30:
            emoji = "🔥🔥 HOT"
        else:
            emoji = "🔥 HEATING UP"

        # Build post
        post = f"{emoji}\n\n"

        if celebrity:
            post += f"🎯 {celebrity}\n"

        post += f"🌡️ {temp}°\n\n"

        # Add title (truncated if needed)
        remaining = 300 - len(post) - len(url) - 20  # Buffer for hashtags
        if len(title) > remaining:
            title = title[:remaining-3] + "..."

        post += f"📰 {title}\n\n{url}\n\n#gossip"

        return post[:300]

    def post_to_bluesky(self, text):
        """Post with clickable links"""
        if not self.session:
            return False

        # Create URL facets
        facets = []
        url_pattern = r'https?://[^\s]+'
        for match in re.finditer(url_pattern, text):
            facets.append({
                "index": {
                    "byteStart": len(text[:match.start()].encode('utf-8')),
                    "byteEnd": len(text[:match.end()].encode('utf-8'))
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": match.group()
                }]
            })

        post_data = {
            "repo": self.session["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "facets": facets
            }
        }

        headers = {
            "Authorization": f"Bearer {self.session['accessJwt']}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{self.base_url}/com.atproto.repo.createRecord",
                                   json=post_data, headers=headers, timeout=30)
            return response.status_code == 200
        except:
            return False

    def run(self):
        """Main process"""
        logger.info("📡 RSS-Based Bluesky Poster starting...")

        if not self.authenticate():
            print("posts_made=false")
            return

        article = self.get_best_unposted()
        if not article:
            logger.info("❄️ No unposted articles (RSS filtered)")
            print("posts_made=false")
            return

        # Create and post
        post_text = self.create_post_text(article)
        logger.info(f"🚀 Posting: {article['title'][:50]}...")

        if self.post_to_bluesky(post_text):
            logger.info(f"✅ SUCCESS: Posted {article['filename']}")
            print("posts_made=true")
        else:
            logger.error("❌ Post failed")
            print("posts_made=false")

if __name__ == "__main__":
    poster = RSSBlueskyPoster()
    poster.run()
