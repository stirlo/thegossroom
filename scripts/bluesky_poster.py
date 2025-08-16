#!/usr/bin/env python3
"""
Enhanced Bluesky Gossip Poster with Smart Recovery & Temperature System
"""

import requests
import yaml
import json
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class SmartBlueskyPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.base_path = Path.cwd()

    def authenticate(self):
        """Authenticate with Bluesky API"""
        if not self.handle or not self.password:
            logger.error("❌ Bluesky credentials not configured")
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
                logger.info("✅ Bluesky authentication successful")
                return True
            else:
                logger.error(f"❌ Bluesky auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Bluesky auth error: {e}")
            return False

    def clean_yaml_frontmatter(self, content):
        """Clean and fix common YAML frontmatter issues"""
        lines = content.split('\n')

        if not (lines[0].strip() == '---' and '---' in lines[1:]):
            return content

        # Find frontmatter boundaries
        try:
            end_idx = lines[1:].index('---') + 1
            frontmatter_lines = lines[1:end_idx]
            body_lines = lines[end_idx + 1:]
        except ValueError:
            return content

        # Clean frontmatter lines
        cleaned_lines = []
        for line in frontmatter_lines:
            # Fix title quotes
            if line.strip().startswith('title:'):
                title_content = line.split('title:', 1)[1].strip()
                title_content = title_content.strip('\'"')
                title_content = title_content.replace('"', '\\"')
                cleaned_lines.append(f'title: "{title_content}"')
            # Skip recovery data mixed in frontmatter
            elif 'recovered:' in line or 'recovery_date:' in line:
                continue
            else:
                cleaned_lines.append(line)

        # Reconstruct content
        return '---\n' + '\n'.join(cleaned_lines) + '\n---\n' + '\n'.join(body_lines)

    def parse_post_safely(self, file_path):
        """Safely parse a post file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean the content first
            content = self.clean_yaml_frontmatter(content)

            # Split frontmatter and body
            if not content.startswith('---'):
                logger.warning(f"No frontmatter found in {file_path}")
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                logger.warning(f"Invalid frontmatter structure in {file_path}")
                return None

            frontmatter_text = parts[1]
            body = parts[2].strip()

            # Parse YAML with safe loader
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
                if not frontmatter:
                    frontmatter = {}
            except yaml.YAMLError as e:
                logger.error(f"YAML parsing error in {file_path}: {e}")
                return None

            return {
                'frontmatter': frontmatter,
                'body': body,
                'file_path': file_path
            }

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

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
            clean_slug = re.sub(r'-+', '-', clean_slug)
            clean_slug = clean_slug.strip('-')

            if not clean_slug:
                clean_slug = "post"

            return f"https://thegossroom.com/{year}/{month}/{day}/{clean_slug}/"
        except:
            return "https://thegossroom.com"

    def get_unposted_articles(self):
        """Get articles that haven't been posted to Bluesky yet"""
        posted_items = self.load_posted_tracking()
        posts_dir = self.base_path / '_posts'
        unposted = []

        if not posts_dir.exists():
            logger.warning("_posts directory not found")
            return unposted

        for post_file in posts_dir.glob('*.md'):
            # Skip recovered files that might be corrupted
            if 'recovered' in post_file.name:
                logger.info(f"⚠️ Skipping recovered file: {post_file.name}")
                continue

            # Skip if already posted
            if post_file.name in posted_items:
                continue

            post_data = self.parse_post_safely(post_file)
            if not post_data:
                continue

            frontmatter = post_data['frontmatter']

            # Skip if already marked as posted in frontmatter
            if frontmatter.get('bluesky_posted'):
                continue

            # Skip if no title
            if not frontmatter.get('title'):
                logger.warning(f"No title found in {post_file}")
                continue

            # Calculate temperature (prefer temperature over drama_score)
            temperature = frontmatter.get('temperature', frontmatter.get('drama_score', 0))

            # Only post hot content (temperature >= 25)
            if temperature < 25:
                continue

            unposted.append({
                'file_path': post_file,
                'file_name': post_file.name,
                'title': frontmatter['title'],
                'temperature': temperature,
                'date': frontmatter.get('date'),
                'primary_celebrity': frontmatter.get('primary_celebrity', ''),
                'tags': frontmatter.get('tags', []),
                'url': self.generate_post_url(post_file.name)
            })

        # Sort by temperature (hottest first)
        unposted.sort(key=lambda x: x['temperature'], reverse=True)
        return unposted

    def create_facets_for_urls(self, text):
        """Create facets for clickable URLs in Bluesky posts"""
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

    def create_bluesky_post(self, article):
        """Create a Bluesky post from article data"""
        title = article['title']
        temp = article['temperature']
        url = article['url']
        celebrity = article['primary_celebrity'].replace('_', ' ').title() if article['primary_celebrity'] else ""

        # Temperature emoji mapping
        if temp >= 40:
            temp_emoji = "🔥🔥🔥 EXPLOSIVE"
        elif temp >= 30:
            temp_emoji = "🔥🔥 HOT DRAMA"
        elif temp >= 25:
            temp_emoji = "🔥 HEATING UP"
        else:
            temp_emoji = "📈 RISING"

        # Build post text
        post_text = f"{temp_emoji}\n\n"

        if celebrity:
            post_text += f"🎯 {celebrity}\n"

        post_text += f"🌡️ Temperature: {temp}°\n\n"

        # Add title (truncated if needed)
        max_title_length = 300 - len(post_text) - len(f"\n\n{url}\n\n#GossipRoom #CelebrityNews")
        if len(title) > max_title_length:
            title = title[:max_title_length-3] + "..."

        post_text += f"📰 {title}\n\n{url}\n\n"

        # Add dynamic hashtags from article tags
        if article.get('tags') and len(article['tags']) > 0:
            hashtags = []
            for tag in article['tags']:
                clean_tag = tag.replace(' ', '').replace('-', '').replace('_', '')
                clean_tag = ''.join(c for c in clean_tag if c.isalnum())
                if clean_tag and len(clean_tag) > 2:
                    hashtags.append(f"#{clean_tag}")

            # Add hashtags if they fit
            if hashtags:
                hashtag_text = " ".join(hashtags)
                if len(post_text + hashtag_text) <= 300:
                    post_text += hashtag_text
                else:
                    # Add default tags
                    post_text += "#GossipRoom #CelebrityNews"
        else:
            post_text += "#GossipRoom #CelebrityNews"

        # Ensure we're under 300 characters
        return post_text[:300]

    def post_to_bluesky(self, text):
        """Post content to Bluesky with clickable links"""
        if not self.session:
            return False

        # Create facets for clickable URLs
        facets = self.create_facets_for_urls(text)

        post_data = {
            "repo": self.session["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
        }

        # Add facets if URLs found
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
                logger.info("✅ Successfully posted to Bluesky with clickable links")
                return True
            else:
                logger.error(f"❌ Bluesky post failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Bluesky post error: {e}")
            return False

    def mark_as_posted(self, file_path):
        """Mark an article as posted to Bluesky"""
        try:
            post_data = self.parse_post_safely(file_path)
            if not post_data:
                return False

            # Add bluesky_posted flag
            post_data['frontmatter']['bluesky_posted'] = True
            post_data['frontmatter']['bluesky_posted_date'] = datetime.now(timezone.utc).isoformat()

            # Reconstruct file content
            frontmatter_text = yaml.dump(post_data['frontmatter'], default_flow_style=False)
            new_content = f"---\n{frontmatter_text}---\n{post_data['body']}"

            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True

        except Exception as e:
            logger.error(f"Error marking {file_path} as posted: {e}")
            return False

    def run(self):
        """Main posting process"""
        logger.info("🐦 Starting Smart Bluesky Poster...")

        if not self.authenticate():
            return

        # Get unposted articles
        unposted = self.get_unposted_articles()

        if not unposted:
            logger.info("❄️ No unposted hot articles found")
            return

        # Post the hottest article
        article = unposted[0]
        post_text = self.create_bluesky_post(article)

        logger.info(f"🔥 Posting: {article['title']} (Temp: {article['temperature']}°)")
        logger.info(f"📝 Post text: {post_text}")

        # Send to Bluesky
        if self.post_to_bluesky(post_text):
            # Mark as posted in tracking file
            posted_items = self.load_posted_tracking()
            posted_items.append(article['file_name'])
            self.save_posted_tracking(posted_items)

            # Mark as posted in frontmatter
            if self.mark_as_posted(article['file_path']):
                logger.info("✅ Marked article as posted")
            else:
                logger.warning("⚠️ Failed to mark article as posted")

            logger.info(f"🎉 Successfully posted: {article['title'][:50]}...")
        else:
            logger.error("❌ Failed to post to Bluesky")

if __name__ == "__main__":
    poster = SmartBlueskyPoster()
    poster.run()
