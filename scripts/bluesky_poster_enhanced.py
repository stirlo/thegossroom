#!/usr/bin/env python3
"""
Bulletproof Bluesky Gossip Poster - Tracking File Priority
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

class BulletproofBlueskyPoster:
    def __init__(self):
        self.base_url = "https://bsky.social/xrpc"
        self.handle = os.getenv('BLUESKY_HANDLE')
        self.password = os.getenv('BLUESKY_PASSWORD')
        self.session = None
        self.base_path = Path.cwd()
        self.site_base_url = "https://thegossroom.com"

        # Primary duplicate prevention - tracking file
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
        """Validate that a URL is accessible"""
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)

            if 200 <= response.status_code < 400:
                logger.info(f"✅ URL validated: {url}")
                return True
            else:
                logger.warning(f"⚠️ URL returned {response.status_code}: {url}")
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"⏰ URL validation timeout: {url}")
            return False
        except Exception as e:
            logger.warning(f"❌ URL validation failed: {url} - {e}")
            return False

    def load_posted_tracking(self):
        """Load posted tracking - BULLETPROOF version"""
        posted_items = set()

        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    data = yaml.safe_load(f) or []

                if isinstance(data, list):
                    posted_items = set(data)
                    logger.info(f"📚 Loaded {len(posted_items)} posted items from tracking file")
                else:
                    logger.warning("⚠️ Unexpected tracking format, starting fresh")

            except Exception as e:
                logger.error(f"❌ Error loading tracking file: {e}")

        # Also check for frontmatter markers as backup
        posts_dir = self.base_path / '_posts'
        if posts_dir.exists():
            frontmatter_posted = 0
            for post_file in posts_dir.glob('*.md'):
                try:
                    with open(post_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if 'bluesky_posted: true' in content:
                        posted_items.add(post_file.name)
                        frontmatter_posted += 1

                except Exception:
                    continue

            if frontmatter_posted > 0:
                logger.info(f"📝 Found {frontmatter_posted} additional posted items from frontmatter")

        logger.info(f"🛡️ Total protected items: {len(posted_items)}")
        return posted_items

    def save_posted_tracking(self, posted_items):
        """Save tracking - BULLETPROOF with backup"""
        self.posted_file.parent.mkdir(exist_ok=True)

        # Convert to sorted list, keep recent items
        posted_list = sorted(list(posted_items))[-500:]  # Keep more for safety

        # Primary save
        try:
            with open(self.posted_file, 'w') as f:
                yaml.dump(posted_list, f, default_flow_style=False)
            logger.info(f"✅ Saved {len(posted_list)} items to tracking file")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to save tracking file: {e}")
            return False

        # Backup save
        backup_file = self.posted_file.with_suffix('.yml.backup')
        try:
            with open(backup_file, 'w') as f:
                yaml.dump(posted_list, f, default_flow_style=False)
            logger.info("💾 Backup tracking file saved")
        except Exception as e:
            logger.warning(f"⚠️ Backup save failed: {e}")

        return True

    def parse_post_safely(self, file_path):
        """Safely parse post with minimal processing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                return None

            try:
                frontmatter = yaml.safe_load(parts[1])
                if not frontmatter:
                    return None
            except yaml.YAMLError as e:
                logger.error(f"YAML error in {file_path.name}: {e}")
                return None

            return {
                'frontmatter': frontmatter,
                'body': parts[2].strip(),
                'file_path': file_path
            }

        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {e}")
            return None

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

    def get_unposted_articles(self):
        """Get unposted articles with bulletproof duplicate detection"""
        posted_items = self.load_posted_tracking()
        posts_dir = self.base_path / '_posts'
        unposted = []

        if not posts_dir.exists():
            logger.warning("_posts directory not found")
            return unposted

        logger.info(f"🔍 Scanning for unposted articles...")

        for post_file in posts_dir.glob('*.md'):
            # PRIMARY CHECK: Tracking file
            if post_file.name in posted_items:
                logger.debug(f"🛡️ BLOCKED by tracking: {post_file.name}")
                continue

            # Skip recovered files
            if 'recovered' in post_file.name:
                continue

            post_data = self.parse_post_safely(post_file)
            if not post_data:
                continue

            frontmatter = post_data['frontmatter']

            # SECONDARY CHECK: Frontmatter
            if frontmatter.get('bluesky_posted'):
                logger.debug(f"🛡️ BLOCKED by frontmatter: {post_file.name}")
                # Add to tracking for consistency
                posted_items.add(post_file.name)
                continue

            # Skip if no title
            if not frontmatter.get('title'):
                continue

            # Temperature check
            temperature = frontmatter.get('temperature', frontmatter.get('drama_score', 0))
            if temperature < 25:
                continue

            # URL validation
            url = self.generate_post_url(post_file.name)
            if not self.validate_url(url, timeout=5):
                continue

            file_date = datetime.fromtimestamp(post_file.stat().st_mtime, tz=timezone.utc)

            unposted.append({
                'file_path': post_file,
                'file_name': post_file.name,
                'title': frontmatter['title'],
                'temperature': temperature,
                'file_date': file_date,
                'primary_celebrity': frontmatter.get('primary_celebrity', ''),
                'tags': frontmatter.get('tags', []),
                'url': url
            })

        # Update tracking with any new frontmatter findings
        if len(posted_items) > len(self.load_posted_tracking()):
            self.save_posted_tracking(posted_items)

        # Sort by temperature, then date
        unposted.sort(key=lambda x: (x['temperature'], x['file_date']), reverse=True)

        logger.info(f"🔥 Found {len(unposted)} unposted hot articles")
        return unposted

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

    def create_bluesky_post(self, article):
        """Create Bluesky post text"""
        title = article['title']
        temp = article['temperature']
        url = article['url']
        celebrity = article['primary_celebrity'].replace('_', ' ').title() if article['primary_celebrity'] else ""

        # Temperature emoji
        if temp >= 40:
            temp_emoji = "🔥🔥🔥 EXPLOSIVE"
        elif temp >= 30:
            temp_emoji = "🔥🔥 HOT DRAMA"
        else:
            temp_emoji = "🔥 HEATING UP"

        # Build post
        post_text = f"{temp_emoji}\n\n"

        if celebrity:
            post_text += f"🎯 {celebrity}\n"

        post_text += f"🌡️ Temperature: {temp}°\n\n"

        # Title (truncated if needed)
        max_title_length = 300 - len(post_text) - len(f"\n\n{url}\n\n#gossip")
        if len(title) > max_title_length:
            title = title[:max_title_length-3] + "..."

        post_text += f"📰 {title}\n\n{url}\n\n"

        # Simple hashtags
        if celebrity:
            clean_celeb = ''.join(c for c in celebrity if c.isalnum())
            if len(clean_celeb) > 2:
                post_text += f"#{clean_celeb.lower()} #gossip"
            else:
                post_text += "#gossip #celebrity"
        else:
            post_text += "#gossip #celebrity"

        return post_text[:300]

    def post_to_bluesky(self, text):
        """Post to Bluesky with clickable links"""
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
                logger.info("✅ Successfully posted to Bluesky")
                return True
            else:
                logger.error(f"❌ Bluesky post failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Bluesky post error: {e}")
            return False

    def mark_as_posted(self, article):
        """BULLETPROOF marking - tracking file is PRIMARY"""
        filename = article['file_name']

        # STEP 1: Update tracking file (CRITICAL)
        posted_items = self.load_posted_tracking()
        posted_items.add(filename)

        if not self.save_posted_tracking(posted_items):
            logger.error(f"🚨 CRITICAL: Failed to save tracking for {filename}")
            return False

        logger.info(f"✅ PROTECTED: {filename} added to tracking file")

        # STEP 2: Try to update frontmatter (OPTIONAL)
        try:
            file_path = Path(article['file_path'])
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple string replacement approach
            if 'bluesky_posted:' not in content:
                # Find the end of frontmatter
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter_section = parts[1]
                    body_section = parts[2]

                    # Add bluesky_posted to frontmatter
                    new_frontmatter = frontmatter_section.rstrip() + f"\nbluesky_posted: true\nbluesky_posted_date: '{datetime.now(timezone.utc).isoformat()}'\n"
                    new_content = f"---{new_frontmatter}---{body_section}"

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    logger.info(f"✅ Updated frontmatter for {filename}")
                else:
                    logger.warning(f"⚠️ Could not parse frontmatter for {filename}")
            else:
                logger.info(f"ℹ️ Frontmatter already marked for {filename}")

        except Exception as e:
            logger.warning(f"⚠️ Frontmatter update failed for {filename}: {e}")
            # Don't fail - tracking file is the primary protection

        return True

    def run(self):
        """Main posting process"""
        logger.info("🛡️ Starting Bulletproof Bluesky Poster...")

        if not self.authenticate():
            print("::set-output name=posts_made::false")
            return

        unposted = self.get_unposted_articles()

        if not unposted:
            logger.info("❄️ No unposted hot articles found")
            print("::set-output name=posts_made::false")
            return

        # Post the hottest article
        article = unposted[0]

        # Final URL check
        if not self.validate_url(article['url']):
            logger.error(f"❌ Final URL validation failed, aborting")
            print("::set-output name=posts_made::false")
            return

        # Create post
        post_text = self.create_bluesky_post(article)

        logger.info(f"🔥 Posting: {article['title'][:50]}... (Temp: {article['temperature']}°)")
        logger.info(f"📝 Post text: {post_text}")

        # Post and mark
        if self.post_to_bluesky(post_text):
            if self.mark_as_posted(article):
                logger.info(f"🎉 SUCCESS: {article['title'][:50]}...")
                print("::set-output name=posts_made::true")
            else:
                logger.error("🚨 POSTED but FAILED to mark - DUPLICATE RISK!")
                print("::set-output name=posts_made::false")
        else:
            logger.error("❌ Failed to post")
            print("::set-output name=posts_made::false")

if __name__ == "__main__":
    poster = BulletproofBlueskyPoster()
    poster.run()
