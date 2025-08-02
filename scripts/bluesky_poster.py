#!/usr/bin/env python3
"""
High-Frequency Bluesky Gossip Poster - Posts twice per hour
Prioritizes: 1) Hottest drama score, 2) Newest posts
"""

import requests
import yaml
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class HighFrequencyGossipPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.base_path = Path.cwd()

    def authenticate(self):
        """Authenticate with Bluesky API"""
        if not self.handle or not self.password:
            print("❌ Bluesky credentials not configured")
            return False

        auth_data = {
            "identifier": self.handle,
            "password": self.password
        }

        try:
            response = requests.post(f"{self.base_url}/com.atproto.server.createSession", 
                                   json=auth_data, timeout=30)

            if response.status_code == 200:
                self.session = response.json()
                print("✅ Bluesky authentication successful")
                return True
            else:
                print(f"❌ Bluesky auth failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bluesky auth error: {e}")
            return False

    def load_posted_tracking(self):
        """Load list of already posted items"""
        posted_file = self.base_path / '_data' / 'bluesky_posted.yml'
        if posted_file.exists():
            try:
                with open(posted_file, 'r') as f:
                    return yaml.safe_load(f) or []
            except:
                return []
        return []

    def save_posted_tracking(self, posted_items):
        """Save updated posted tracking"""
        posted_file = self.base_path / '_data' / 'bluesky_posted.yml'
        posted_file.parent.mkdir(exist_ok=True)

        # Keep only last 300 items for high-frequency posting
        posted_items = posted_items[-300:]

        with open(posted_file, 'w') as f:
            yaml.dump(posted_items, f, default_flow_style=False)

    def generate_post_url(self, filename):
        """Generate Jekyll post URL from filename"""
        # Example: 2025-08-02-khloe-kardashian-drama.md
        # Becomes: https://thegossroom.com/gossip/2025/08/02/khloe-kardashian-drama.html

        if not filename.endswith('.md'):
            return "https://thegossroom.com"

        # Extract date and slug
        name_without_ext = filename[:-3]  # Remove .md

        if len(name_without_ext) < 10:
            return "https://thegossroom.com"

        date_part = name_without_ext[:10]  # 2025-08-02
        slug_part = name_without_ext[11:]  # khloe-kardashian-drama

        try:
            year, month, day = date_part.split('-')
            return f"https://thegossroom.com/gossip/{year}/{month}/{day}/{slug_part}.html"
        except:
            return "https://thegossroom.com"

    def find_best_gossip(self):
        """Find best unposted gossip: HOTTEST first, then NEWEST"""
        posted_items = self.load_posted_tracking()
        posts_dir = self.base_path / '_posts'

        if not posts_dir.exists():
            print("📁 No _posts directory found")
            return None

        candidates = []

        # Check posts from last 72 hours for high-frequency posting
        cutoff_time = datetime.now() - timedelta(hours=72)

        for post_file in posts_dir.glob('*.md'):
            if post_file.name in posted_items:
                continue

            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if content.startswith('---'):
                    # Parse front matter
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        front_matter = yaml.safe_load(parts[1])

                        drama_score = front_matter.get('drama_score', 0)
                        post_date = front_matter.get('date')

                        # Lower threshold for high-frequency posting
                        if drama_score >= 5:  # Accept lower drama scores
                            # Parse date for sorting
                            try:
                                if isinstance(post_date, str):
                                    post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                                else:
                                    post_datetime = post_date or datetime.now()
                            except:
                                post_datetime = datetime.now()

                            candidates.append({
                                'file': post_file.name,
                                'title': front_matter.get('title', ''),
                                'drama_score': drama_score,
                                'post_date': post_datetime,
                                'primary_celebrity': front_matter.get('primary_celebrity', ''),
                                'source_url': front_matter.get('source_url', ''),
                                'tags': front_matter.get('tags', []),
                                'excerpt': front_matter.get('excerpt', ''),
                                'post_url': self.generate_post_url(post_file.name)  # NEW: Generate direct link
                            })

            except Exception as e:
                print(f"⚠️ Error parsing {post_file.name}: {e}")
                continue

        if not candidates:
            print("📭 No eligible gossip found")
            return None

        # SORT BY: 1) Drama Score (DESC), 2) Date (DESC - newest first)
        candidates.sort(key=lambda x: (-x['drama_score'], -x['post_date'].timestamp()))

        best_gossip = candidates[0]
        print(f"🎯 Selected: Score {best_gossip['drama_score']}, Date {best_gossip['post_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"🔗 Direct link: {best_gossip['post_url']}")

        return best_gossip

    def create_bluesky_post(self, gossip):
        """Create engaging Bluesky post text"""
        celebrity = gossip['primary_celebrity'].replace('_', ' ').title() if gossip['primary_celebrity'] else "Celebrity"

        # Drama level indicators (adjusted for high-frequency posting)
        if gossip['drama_score'] >= 40:
            drama_emoji = "🔥🔥🔥 EXPLOSIVE"
        elif gossip['drama_score'] >= 25:
            drama_emoji = "🔥🔥 HOT DRAMA"
        elif gossip['drama_score'] >= 15:
            drama_emoji = "🔥 HEATING UP"
        elif gossip['drama_score'] >= 10:
            drama_emoji = "🎭 DRAMA ALERT"
        else:
            drama_emoji = "📰 BREAKING"

        # Build post text
        post_text = f"{drama_emoji}\n\n"

        if celebrity != "Celebrity":
            post_text += f"🎯 {celebrity}\n"

        post_text += f"📊 Drama Score: {gossip['drama_score']}\n\n"

        # Add title (truncated if needed)
        title = gossip['title'][:100] + "..." if len(gossip['title']) > 100 else gossip['title']
        post_text += f"📰 {title}\n\n"

        # NEW: Use direct post URL instead of homepage
        post_text += f"🔗 {gossip['post_url']}\n\n"
        post_text += "#CelebrityGossip #Drama #Entertainment #TheGossipRoom"

        # Bluesky has 300 character limit
        return post_text[:300]

    def post_to_bluesky(self, text):
        """Post content to Bluesky"""
        if not self.session:
            return False

        post_data = {
            "repo": self.session["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now().isoformat() + "Z"
            }
        }

        headers = {
            "Authorization": f"Bearer {self.session['accessJwt']}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{self.base_url}/com.atproto.repo.createRecord",
                                   json=post_data, headers=headers, timeout=30)

            if response.status_code == 200:
                print("✅ Successfully posted to Bluesky")
                return True
            else:
                print(f"❌ Bluesky post failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bluesky post error: {e}")
            return False

    def run(self):
        """Main high-frequency posting process"""
        print("🎭 Starting High-Frequency Bluesky Gossip Poster...")

        if not self.authenticate():
            return

        best_gossip = self.find_best_gossip()
        if not best_gossip:
            print("📭 No gossip to post (all recent posts already shared)")
            return

        print(f"🎯 Found gossip: {best_gossip['title'][:50]}... (Score: {best_gossip['drama_score']})")

        post_text = self.create_bluesky_post(best_gossip)

        if self.post_to_bluesky(post_text):
            # Mark as posted
            posted_items = self.load_posted_tracking()
            posted_items.append(best_gossip['file'])
            self.save_posted_tracking(posted_items)
            print(f"🎉 Posted to Bluesky: {best_gossip['title'][:50]}...")
        else:
            print("❌ Failed to post to Bluesky")

if __name__ == "__main__":
    poster = HighFrequencyGossipPoster()
    poster.run()
