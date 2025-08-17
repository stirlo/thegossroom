#!/usr/bin/env python3
"""
Ultra-Simple Bluesky Poster - Tracking File Only
"""

import requests
import yaml
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class SimpleBlueskyPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.site_base_url = "https://thegossroom.com"

        # ONLY tracking file - no frontmatter complexity
        self.posted_file = Path('_data/bluesky_posted.yml')

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

    def load_posted_items(self):
        """Load simple tracking list"""
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    data = yaml.safe_load(f) or []
                return set(data) if isinstance(data, list) else set()
            except:
                return set()
        return set()

    def save_posted_items(self, posted_set):
        """Save simple tracking list"""
        self.posted_file.parent.mkdir(exist_ok=True)
        posted_list = sorted(list(posted_set))[-400:]  # Keep last 400

        try:
            with open(self.posted_file, 'w') as f:
                yaml.dump(posted_list, f, default_flow_style=False)
            logger.info(f"💾 Saved {len(posted_list)} tracked items")
            return True
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            return False

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
        """Get the hottest unposted article"""
        posted = self.load_posted_items()
        posts_dir = Path('_posts')

        if not posts_dir.exists():
            return None

        candidates = []

        for post_file in posts_dir.glob('*.md'):
            # Skip if already posted
            if post_file.name in posted:
                continue

            # Skip recovered files
            if 'recovered' in post_file.name:
                continue

            # Parse frontmatter
            fm = self.parse_post(post_file)
            if not fm or not fm.get('title'):
                continue

            # Check temperature
            temp = fm.get('temperature', fm.get('drama_score', 0))
            if temp < 25:
                continue

            # Generate and validate URL
            url = self.generate_url(post_file.name)
            if not url or not self.validate_url(url):
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
        return max(candidates, key=lambda x: x['temperature'])

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
        logger.info("🚀 Simple Bluesky Poster starting...")

        if not self.authenticate():
            print("posts_made=false")
            return

        article = self.get_best_unposted()
        if not article:
            logger.info("❄️ No unposted articles")
            print("posts_made=false")
            return

        # Create post
        post_text = self.create_post_text(article)
        logger.info(f"🔥 Posting: {article['title'][:50]}... (Temp: {article['temperature']}°)")

        # Post to Bluesky
        if self.post_to_bluesky(post_text):
            # Mark as posted
            posted = self.load_posted_items()
            posted.add(article['filename'])

            if self.save_posted_items(posted):
                logger.info(f"✅ SUCCESS: {article['filename']}")
                print("posts_made=true")
            else:
                logger.error("🚨 Posted but tracking failed!")
                print("posts_made=false")
        else:
            logger.error("❌ Post failed")
            print("posts_made=false")

if __name__ == "__main__":
    poster = SimpleBlueskyPoster()
    poster.run()
