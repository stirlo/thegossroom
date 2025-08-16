#!/usr/bin/env python3
"""
Temperature-Based Bluesky Gossip Poster
Only posts the HOTTEST stories with live temperature calculation
"""

import requests
import yaml
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

class TemperatureBasedPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.base_path = Path.cwd()
        self.celebrities = self.load_celebrities()

    def load_celebrities(self):
        """Load current celebrity temperatures"""
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def calculate_live_temperature(self, post_data):
        """Calculate real-time temperature based on current celebrity scores"""
        base_score = post_data.get('drama_score', 0)

        # Get celebrity boost
        celebrity_boost = 0
        mentions = post_data.get('mentions', {})

        if mentions:
            for celeb_key, mention_count in mentions.items():
                celeb_temp = self.celebrities.get(celeb_key, {}).get('drama_score', 0)
                celebrity_boost += celeb_temp * mention_count

            # Average the celebrity boost
            celebrity_boost = celebrity_boost / len(mentions)

        # Time decay factor
        post_date = post_data.get('date')
        if isinstance(post_date, str):
            try:
                post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                hours_old = (datetime.now() - post_datetime.replace(tzinfo=None)).total_seconds() / 3600

                if hours_old < 6:
                    time_factor = 1.0
                elif hours_old < 24:
                    time_factor = 0.8
                elif hours_old < 72:
                    time_factor = 0.5
                else:
                    time_factor = 0.2
            except:
                time_factor = 1.0
        else:
            time_factor = 1.0

        # Calculate final temperature
        temperature = (base_score + (celebrity_boost * 0.5)) * time_factor
        return min(100, int(temperature))

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
        """Load posted tracking with temperature history"""
        posted_file = self.base_path / '_data' / 'bluesky_posted.yml'
        if posted_file.exists():
            try:
                with open(posted_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    return data.get('posted_files', []), data.get('posting_history', [])
            except:
                return [], []
        return [], []

    def save_posted_tracking(self, posted_files, posting_history):
        """Save posted tracking with temperature data"""
        posted_file = self.base_path / '_data' / 'bluesky_posted.yml'
        posted_file.parent.mkdir(exist_ok=True)

        # Keep last 500 posted files and 100 history entries
        data = {
            'posted_files': posted_files[-500:],
            'posting_history': posting_history[-100:],
            'last_updated': datetime.now().isoformat()
        }

        with open(posted_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def find_hottest_gossip(self):
        """Find the hottest unposted gossip using live temperature calculation"""
        posted_files, posting_history = self.load_posted_tracking()
        posts_dir = self.base_path / '_posts'

        if not posts_dir.exists():
            print("📁 No _posts directory found")
            return None

        candidates = []

        # Only consider posts from last 6 hours for peak freshness
        cutoff_time = datetime.now() - timedelta(hours=6)

        for post_file in posts_dir.glob('*.md'):
            if post_file.name in posted_files:
                continue

            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        front_matter = yaml.safe_load(parts[1])

                        # Calculate live temperature
                        temperature = self.calculate_live_temperature(front_matter)

                        # Only consider posts with temperature >= 50
                        if temperature >= 50:
                            post_date = front_matter.get('date')
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
                                'temperature': temperature,
                                'drama_score': front_matter.get('drama_score', 0),
                                'post_date': post_datetime,
                                'primary_celebrity': front_matter.get('primary_celebrity', ''),
                                'mentions': front_matter.get('mentions', {}),
                                'tags': front_matter.get('tags', []),
                                'post_url': self.generate_post_url(post_file.name)
                            })

            except Exception as e:
                print(f"⚠️ Error parsing {post_file.name}: {e}")
                continue

        if not candidates:
            print("🌡️ No hot gossip found (temperature < 50°)")
            return None

        # Sort by temperature first, then by recency
        candidates.sort(key=lambda x: (-x['temperature'], -x['post_date'].timestamp()))

        hottest = candidates[0]
        print(f"🔥 HOTTEST: {hottest['title'][:50]}...")
        print(f"🌡️ Temperature: {hottest['temperature']}° (Drama: {hottest['drama_score']})")
        print(f"📅 Posted: {hottest['post_date'].strftime('%Y-%m-%d %H:%M')}")

        return hottest

    def generate_post_url(self, filename):
        """Generate Jekyll post URL from filename"""
        if not filename.endswith('.md'):
            return "https://thegossroom.com"

        name_without_ext = filename[:-3]
        if len(name_without_ext) < 10:
            return "https://thegossroom.com"

        date_part = name_without_ext[:10]
        slug_part = name_without_ext[11:]

        try:
            year, month, day = date_part.split('-')
            clean_slug = slug_part.rstrip('-').rstrip('_')
            clean_slug = re.sub(r'-+', '-', clean_slug).strip('-')

            if not clean_slug:
                clean_slug = "post"

            return f"https://thegossroom.com/{year}/{month}/{day}/{clean_slug}/"
        except:
            return "https://thegossroom.com"

    def create_temperature_post(self, gossip):
        """Create Bluesky post with temperature emphasis"""
        celebrity = gossip['primary_celebrity'].replace('_', ' ').title() if gossip['primary_celebrity'] else "Celebrity"
        temp = gossip['temperature']

        # Temperature-based emoji
        if temp >= 90:
            temp_emoji = "🔥🔥🔥 NUCLEAR"
        elif temp >= 75:
            temp_emoji = "🔥🔥 EXPLOSIVE"
        elif temp >= 60:
            temp_emoji = "🔥 BLAZING"
        else:
            temp_emoji = "🌡️ HEATING UP"

        post_text = f"{temp_emoji}\n\n"

        if celebrity != "Celebrity":
            post_text += f"🎯 {celebrity}\n"

        post_text += f"🌡️ Temperature: {temp}°\n\n"

        # Truncate title to fit
        title = gossip['title'][:80] + "..." if len(gossip['title']) > 80 else gossip['title']
        post_text += f"📰 {title}\n\n"
        post_text += f"{gossip['post_url']}\n\n"

        # Add relevant hashtags
        hashtags = ["#GossipRoom", "#CelebDrama"]
        if celebrity != "Celebrity":
            celeb_tag = f"#{celebrity.replace(' ', '')}"
            hashtags.append(celeb_tag)

        hashtag_text = " ".join(hashtags)
        if len(post_text + hashtag_text) <= 300:
            post_text += hashtag_text

        return post_text[:300]

    def create_facets_for_urls(self, text):
        """Create facets for clickable URLs"""
        url_pattern = r'https?://[^\s]+'
        urls = list(re.finditer(url_pattern, text))

        facets = []
        for match in urls:
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

        return facets

    def post_to_bluesky(self, text):
        """Post to Bluesky with facets"""
        if not self.session:
            return False

        facets = self.create_facets_for_urls(text)

        post_data = {
            "repo": self.session["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now().isoformat() + "Z"
            }
        }

        if facets:
            post_data["record"]["facets"] = facets

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
        """Main temperature-based posting process"""
        print("🌡️ Starting Temperature-Based Bluesky Poster...")

        if not self.authenticate():
            return

        hottest_gossip = self.find_hottest_gossip()
        if not hottest_gossip:
            print("❄️ No hot gossip to post (all stories below 50° temperature)")
            return

        post_text = self.create_temperature_post(hottest_gossip)

        if self.post_to_bluesky(post_text):
            posted_files, posting_history = self.load_posted_tracking()

            # Add to posted files
            posted_files.append(hottest_gossip['file'])

            # Add to posting history
            posting_history.append({
                'file': hottest_gossip['file'],
                'title': hottest_gossip['title'],
                'temperature': hottest_gossip['temperature'],
                'celebrity': hottest_gossip['primary_celebrity'],
                'posted_at': datetime.now().isoformat()
            })

            self.save_posted_tracking(posted_files, posting_history)
            print(f"🎉 Posted: {hottest_gossip['title'][:50]}... (🌡️{hottest_gossip['temperature']}°)")
        else:
            print("❌ Failed to post to Bluesky")

if __name__ == "__main__":
    poster = TemperatureBasedPoster()
    poster.run()
