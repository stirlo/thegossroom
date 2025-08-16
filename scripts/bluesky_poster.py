#!/usr/bin/env python3
"""
Bluesky Poster - Only posts from active _posts/ directory
"""

import requests
import yaml
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlueSkyPoster:
    def __init__(self):
        self.base_path = Path('.')
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None

        if not self.handle or not self.password:
            raise ValueError("BLUESKY_HANDLE and BLUESKY_PASSWORD must be set")

    def authenticate(self):
        """Authenticate with Bluesky"""
        try:
            response = requests.post(
                'https://bsky.social/xrpc/com.atproto.server.createSession',
                json={
                    'identifier': self.handle,
                    'password': self.password
                }
            )
            response.raise_for_status()
            self.session = response.json()
            logger.info("✅ Authenticated with Bluesky")
            return True
        except Exception as e:
            logger.error(f"❌ Bluesky authentication failed: {e}")
            return False

    def get_hottest_unposted_article(self):
        """Get the hottest article from _posts/ that hasn't been posted to Bluesky"""
        posts_dir = self.base_path / '_posts'

        # Load posted articles
        try:
            with open('data/bluesky_posted.json', 'r') as f:
                posted_articles = set(json.load(f))
        except FileNotFoundError:
            posted_articles = set()

        # Find hottest unposted article from active posts only
        hottest_post = None
        highest_temp = 0

        for post_file in posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.startswith('---'):
                    continue

                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue

                front_matter = yaml.safe_load(parts[1])

                # Skip if already posted
                post_id = post_file.name
                if post_id in posted_articles:
                    continue

                # Check temperature
                temperature = front_matter.get('temperature', 0)
                if temperature > highest_temp:
                    highest_temp = temperature
                    hottest_post = {
                        'file': post_file,
                        'filename': post_file.name,
                        'title': front_matter.get('title', 'Untitled'),
                        'temperature': temperature,
                        'source_url': front_matter.get('source_url', ''),
                        'primary_celebrity': front_matter.get('primary_celebrity', ''),
                        'date': front_matter.get('date', ''),
                        'site_url': f"https://stirlo.github.io/thegossroom/{post_file.stem}/"
                    }

            except Exception as e:
                logger.error(f"Error processing {post_file}: {e}")
                continue

        if hottest_post:
            logger.info(f"🔥 Hottest unposted: {hottest_post['title'][:50]}... (🌡️{hottest_post['temperature']}°)")
        else:
            logger.info("❄️ No unposted articles found")

        return hottest_post

    def create_post_text(self, article):
        """Create Bluesky post text"""
        title = article['title']
        temp = article['temperature']
        celeb = article['primary_celebrity']

        # Temperature emoji
        if temp >= 90:
            temp_emoji = "🔥🔥🔥"
        elif temp >= 70:
            temp_emoji = "🔥🔥"
        elif temp >= 50:
            temp_emoji = "🔥"
        else:
            temp_emoji = "☕"

        # Create post
        post_text = f"{temp_emoji} {title}"

        if celeb:
            post_text += f"\n\n#{celeb.replace(' ', '')}"

        post_text += f"\n\n🌡️ {temp}° | Read more: {article['site_url']}"

        # Ensure under 300 characters
        if len(post_text) > 280:
            title_limit = 280 - len(post_text) + len(title) - 3
            post_text = f"{temp_emoji} {title[:title_limit]}..."
            if celeb:
                post_text += f"\n\n#{celeb.replace(' ', '')}"
            post_text += f"\n\n🌡️ {temp}° | Read more: {article['site_url']}"

        return post_text

    def post_to_bluesky(self, article):
        """Post article to Bluesky"""
        if not self.session:
            return False

        post_text = self.create_post_text(article)

        try:
            response = requests.post(
                'https://bsky.social/xrpc/com.atproto.repo.createRecord',
                headers={
                    'Authorization': f"Bearer {self.session['accessJwt']}"
                },
                json={
                    'repo': self.session['did'],
                    'collection': 'app.bsky.feed.post',
                    'record': {
                        'text': post_text,
                        'createdAt': datetime.now().isoformat() + 'Z'
                    }
                }
            )
            response.raise_for_status()

            logger.info(f"✅ Posted to Bluesky: {article['title'][:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to post to Bluesky: {e}")
            return False

    def mark_as_posted(self, article):
        """Mark article as posted"""
        Path('data').mkdir(exist_ok=True)

        try:
            with open('data/bluesky_posted.json', 'r') as f:
                posted_articles = json.load(f)
        except FileNotFoundError:
            posted_articles = []

        posted_articles.append(article['filename'])

        with open('data/bluesky_posted.json', 'w') as f:
            json.dump(posted_articles, f, indent=2)

    def run(self):
        """Main execution"""
        logger.info("🐦 Starting Bluesky Poster...")

        if not self.authenticate():
            return

        article = self.get_hottest_unposted_article()

        if not article:
            logger.info("📭 No new articles to post")
            return

        if self.post_to_bluesky(article):
            self.mark_as_posted(article)
            logger.info("🎉 Bluesky posting complete!")
        else:
            logger.error("💥 Bluesky posting failed!")

if __name__ == "__main__":
    poster = BlueSkyPoster()
    poster.run()
