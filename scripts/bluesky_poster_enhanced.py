#!/usr/bin/env python3
"""
Enhanced Bluesky Gossip Poster with Smart Recovery, Temperature System & URL Validation
"""

import requests
import yaml
import json
import os
import re
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

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
        self.site_base_url = "https://thegossroom.com"

        # Queue management
        self.queue_file = self.base_path / '_data' / 'bluesky_queue.yml'
        self.posted_file = self.base_path / '_data' / 'bluesky_posted.yml'

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

    def validate_url(self, url, timeout=10):
        """Validate that a URL is accessible before posting"""
        try:
            # Quick HEAD request to check if URL exists
            response = requests.head(url, timeout=timeout, allow_redirects=True)

            # Accept 2xx and 3xx status codes
            if 200 <= response.status_code < 400:
                logger.info(f"✅ URL validated: {url}")
                return True
            else:
                logger.warning(f"⚠️ URL returned {response.status_code}: {url}")
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"⏰ URL validation timeout: {url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ URL validation failed: {url} - {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error validating URL: {url} - {e}")
            return False

    def clean_yaml_frontmatter(self, content):
        """Clean and fix common YAML frontmatter issues"""
        lines = content.split('\n')

        if not (lines[0].strip() == '---' and '---' in lines[1:]):
            return content

        try:
            end_idx = lines[1:].index('---') + 1
            frontmatter_lines = lines[1:end_idx]
            body_lines = lines[end_idx + 1:]
        except ValueError:
            return content

        cleaned_lines = []
        for line in frontmatter_lines:
            if line.strip().startswith('title:'):
                title_content = line.split('title:', 1)[1].strip()
                title_content = title_content.strip('\'"')
                title_content = title_content.replace('"', '\\"')
                cleaned_lines.append(f'title: "{title_content}"')
            elif 'recovered:' in line or 'recovery_date:' in line:
                continue
            else:
                cleaned_lines.append(line)

        return '---\n' + '\n'.join(cleaned_lines) + '\n---\n' + '\n'.join(body_lines)

    def parse_post_safely(self, file_path):
        """Safely parse a post file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content = self.clean_yaml_frontmatter(content)

            if not content.startswith('---'):
                logger.warning(f"No frontmatter found in {file_path}")
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                logger.warning(f"Invalid frontmatter structure in {file_path}")
                return None

            frontmatter_text = parts[1]
            body = parts[2].strip()

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
        """Load comprehensive posted tracking with timestamps"""
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    data = yaml.safe_load(f) or {}

                # Handle both old format (list) and new format (dict)
                if isinstance(data, list):
                    # Convert old format to new format
                    return {item: datetime.now(timezone.utc).isoformat() for item in data}
                elif isinstance(data, dict):
                    return data.get('posted_items', {})
                else:
                    return {}
            except Exception as e:
                logger.error(f"Error loading posted tracking: {e}")
                return {}
        return {}

    def save_posted_tracking(self, posted_items):
        """Save comprehensive posted tracking"""
        self.posted_file.parent.mkdir(exist_ok=True)

        # Clean old entries (keep last 30 days)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        cleaned_items = {}

        for filename, posted_date in posted_items.items():
            try:
                post_datetime = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                if post_datetime >= cutoff_date:
                    cleaned_items[filename] = posted_date
            except:
                # Keep items with invalid dates for safety
                cleaned_items[filename] = posted_date

        data = {
            'posted_items': cleaned_items,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'total_posted': len(cleaned_items)
        }

        with open(self.posted_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def load_queue(self):
        """Load posting queue"""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r') as f:
                    return yaml.safe_load(f) or []
            except Exception as e:
                logger.error(f"Error loading queue: {e}")
                return []
        return []

    def save_queue(self, queue):
        """Save posting queue"""
        self.queue_file.parent.mkdir(exist_ok=True)

        # Clean queue - remove old entries (older than 48 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
        cleaned_queue = []

        for item in queue:
            try:
                queue_time = datetime.fromisoformat(item['queued_at'].replace('Z', '+00:00'))
                if queue_time >= cutoff_time:
                    cleaned_queue.append(item)
            except:
                # Keep items with invalid dates for safety
                cleaned_queue.append(item)

        # Sort by priority (temperature desc, then date desc)
        cleaned_queue.sort(key=lambda x: (x['temperature'], x['file_date']), reverse=True)

        # Keep only top 50 items to prevent queue bloat
        cleaned_queue = cleaned_queue[:50]

        with open(self.queue_file, 'w') as f:
            yaml.dump(cleaned_queue, f, default_flow_style=False)

    def generate_post_url(self, filename):
        """Generate Jekyll post URL from filename"""
        if not filename.endswith('.md'):
            return self.site_base_url

        name_without_ext = filename[:-3]

        if len(name_without_ext) < 10:
            return self.site_base_url

        date_part = name_without_ext[:10]
        slug_part = name_without_ext[11:]

        try:
            year, month, day = date_part.split('-')
            clean_slug = slug_part.rstrip('-').rstrip('_')
            clean_slug = re.sub(r'-+', '-', clean_slug)
            clean_slug = clean_slug.strip('-')

            if not clean_slug:
                clean_slug = "post"

            return f"{self.site_base_url}/{year}/{month}/{day}/{clean_slug}/"
        except:
            return self.site_base_url

    def get_file_creation_time(self, file_path):
        """Get file creation/modification time"""
        try:
            stat = file_path.stat()
            return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        except:
            return datetime.now(timezone.utc)

    def build_posting_queue(self):
        """Build and update the posting queue with all eligible articles"""
        posted_items = self.load_posted_tracking()
        current_queue = self.load_queue()
        posts_dir = self.base_path / '_posts'

        # Get currently queued filenames
        queued_files = {item['file_name'] for item in current_queue}

        new_queue_items = []

        if not posts_dir.exists():
            logger.warning("_posts directory not found")
            return current_queue

        for post_file in posts_dir.glob('*.md'):
            # Skip if already processed
            if post_file.name in posted_items or post_file.name in queued_files:
                continue

            # Skip recovered files
            if 'recovered' in post_file.name:
                continue

            post_data = self.parse_post_safely(post_file)
            if not post_data:
                continue

            frontmatter = post_data['frontmatter']

            # Skip if already marked as posted
            if frontmatter.get('bluesky_posted'):
                continue

            # Skip if no title
            if not frontmatter.get('title'):
                continue

            # Calculate temperature
            temperature = frontmatter.get('temperature', frontmatter.get('drama_score', 0))

            # Only queue hot content (temperature >= 25)
            if temperature < 25:
                continue

            # Generate and validate URL
            url = self.generate_post_url(post_file.name)

            # Skip if URL validation fails (but don't block queue building)
            url_valid = self.validate_url(url, timeout=5)
            if not url_valid:
                logger.warning(f"⚠️ Skipping {post_file.name} - URL validation failed")
                continue

            file_date = self.get_file_creation_time(post_file)

            queue_item = {
                'file_path': str(post_file),
                'file_name': post_file.name,
                'title': frontmatter['title'],
                'temperature': temperature,
                'file_date': file_date.isoformat(),
                'primary_celebrity': frontmatter.get('primary_celebrity', ''),
                'tags': frontmatter.get('tags', []),
                'url': url,
                'queued_at': datetime.now(timezone.utc).isoformat(),
                'url_validated': url_valid
            }

            new_queue_items.append(queue_item)

        # Combine with existing queue
        updated_queue = current_queue + new_queue_items

        # Save updated queue
        self.save_queue(updated_queue)

        logger.info(f"📋 Queue updated: {len(new_queue_items)} new items, {len(updated_queue)} total")
        return updated_queue

    def get_next_post_from_queue(self):
        """Get the next highest priority post from queue"""
        queue = self.load_queue()

        if not queue:
            logger.info("📭 Queue is empty")
            return None

        # Queue is already sorted by priority
        next_post = queue[0]

        # Remove from queue
        remaining_queue = queue[1:]
        self.save_queue(remaining_queue)

        logger.info(f"📤 Next post from queue: {next_post['title'][:50]}... (Temp: {next_post['temperature']}°)")
        return next_post

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

            if hashtags:
                hashtag_text = " ".join(hashtags)
                if len(post_text + hashtag_text) <= 300:
                    post_text += hashtag_text
                else:
                    post_text += "#GossipRoom #CelebrityNews"
        else:
            post_text += "#GossipRoom #CelebrityNews"

        return post_text[:300]

    def post_to_bluesky(self, text):
        """Post content to Bluesky with clickable links"""
        if not self.session:
            return False

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

    def mark_as_posted(self, article):
        """Mark an article as posted to Bluesky"""
        try:
            # Update posted tracking
            posted_items = self.load_posted_tracking()
            posted_items[article['file_name']] = datetime.now(timezone.utc).isoformat()
            self.save_posted_tracking(posted_items)

            # Update frontmatter
            file_path = Path(article['file_path'])
            post_data = self.parse_post_safely(file_path)
            if not post_data:
                return False

            post_data['frontmatter']['bluesky_posted'] = True
            post_data['frontmatter']['bluesky_posted_date'] = datetime.now(timezone.utc).isoformat()

            frontmatter_text = yaml.dump(post_data['frontmatter'], default_flow_style=False)
            new_content = f"---\n{frontmatter_text}---\n{post_data['body']}"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True

        except Exception as e:
            logger.error(f"Error marking {article['file_name']} as posted: {e}")
            return False

    def run(self):
        """Main posting process with queue management"""
        logger.info("🐦 Starting Smart Bluesky Poster with Queue System...")

        if not self.authenticate():
            return

        # Build/update the posting queue
        logger.info("📋 Building posting queue...")
        self.build_posting_queue()

        # Get next post from queue
        article = self.get_next_post_from_queue()

        if not article:
            logger.info("❄️ No posts in queue")
            return

        # Double-check URL before posting
        if not self.validate_url(article['url']):
            logger.error(f"❌ URL validation failed for {article['title']}, skipping")
            return

        # Create and send post
        post_text = self.create_bluesky_post(article)

        logger.info(f"🔥 Posting: {article['title'][:50]}... (Temp: {article['temperature']}°)")
        logger.info(f"📝 Post text: {post_text}")

        if self.post_to_bluesky(post_text):
            if self.mark_as_posted(article):
                logger.info("✅ Marked article as posted")
            else:
                logger.warning("⚠️ Failed to mark article as posted")

            logger.info(f"🎉 Successfully posted: {article['title'][:50]}...")

            # Set GitHub Actions output
            print(f"::set-output name=posts_made::true")
        else:
            logger.error("❌ Failed to post to Bluesky")
            print(f"::set-output name=posts_made::false")

if __name__ == "__main__":
    poster = SmartBlueskyPoster()
    poster.run()
