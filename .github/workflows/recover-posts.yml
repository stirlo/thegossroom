#!/usr/bin/env python3
"""
Post Recovery Script - Convert JSON data to Jekyll posts
Recovers all posts that were saved to JSON but never converted to .md files
"""

import json
import yaml
import re
from datetime import datetime
from pathlib import Path
import logging
import os

# Change to repository root if running from scripts directory
if os.path.basename(os.getcwd()) == 'scripts':
    os.chdir('..')
    print("📁 Changed to repository root directory")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class PostRecovery:
    def __init__(self):
        self.base_path = Path('.')

    def recover_posts_from_json(self):
        """🚀 RECOVERY: Convert existing JSON data to Jekyll posts"""
        try:
            # Load the JSON data
            json_path = 'data/gossip_data.json'
            if not Path(json_path).exists():
                logger.error(f"❌ {json_path} not found!")
                return 0

            with open(json_path, 'r') as f:
                gossip_data = json.load(f)

            entries = gossip_data.get('entries', [])
            logger.info(f"🔍 Found {len(entries)} entries in JSON to recover")

            if not entries:
                logger.info("ℹ️ No entries found in JSON file")
                return 0

            # Ensure _posts directory exists
            posts_dir = self.base_path / '_posts'
            posts_dir.mkdir(exist_ok=True)

            recovered_count = 0
            skipped_count = 0

            for i, entry in enumerate(entries, 1):
                # Extract data from JSON entry
                title = entry.get('title', 'Untitled')
                content = entry.get('content', '')
                link = entry.get('link', '')
                source = entry.get('source', 'unknown')
                drama_score = entry.get('drama_score', 1)
                mentions = entry.get('mentions', {})
                celebrities = entry.get('celebrities', [])
                published = entry.get('published', '')

                # Generate filename
                date_str = datetime.now().strftime('%Y-%m-%d')
                slug = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
                slug = re.sub(r'\s+', '-', slug).lower()[:50]
                filename = f"{date_str}-{slug}-recovered.md"

                filepath = posts_dir / filename

                # Skip if already exists
                if filepath.exists():
                    logger.debug(f"⏭️ Skipping existing: {filename}")
                    skipped_count += 1
                    continue

                # Determine primary celebrity
                primary_celebrity = 'unknown'
                if mentions and isinstance(mentions, dict):
                    primary_celebrity = max(mentions.keys(), key=mentions.get)
                elif celebrities and len(celebrities) > 0:
                    primary_celebrity = str(celebrities[0]).replace(' ', '_')

                # Create tags
                tags = []
                if primary_celebrity != 'unknown':
                    tags.append(primary_celebrity.replace('_', '-'))
                tags.append(f"source-{source}")

                # Drama level
                if drama_score >= 10:
                    drama_level = "explosive"
                elif drama_score >= 5:
                    drama_level = "hot"
                elif drama_score >= 2:
                    drama_level = "rising"
                else:
                    drama_level = "mild"

                tags.append(f"drama-{drama_level}")
                tags.append("recovered")

                # Clean content
                if not content:
                    content = f"Article about {', '.join([str(c) for c in celebrities[:3]])} from {source}."

                # Create celebrity list for display
                celebrity_display = []
                if celebrities:
                    celebrity_display = [str(c).replace('_', ' ').title() for c in celebrities[:5]]
                elif mentions:
                    celebrity_display = [k.replace('_', ' ').title() for k in mentions.keys()][:5]

                # Create frontmatter - FIXED: No backslashes in f-string
                escaped_title = title.replace('"', '\\"')
                recovery_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                current_time_display = datetime.now().strftime('%Y-%m-%d %H:%M')
                source_display = source.replace('_', ' ').title()

                frontmatter = f"""---
layout: post
title: "{escaped_title}"
date: {recovery_timestamp} +0000
categories: gossip
tags: {tags}
drama_score: {drama_score}
primary_celebrity: {primary_celebrity}
source: {source}
source_url: "{link}"
mentions: {mentions if isinstance(mentions, dict) else {}}
recovered: true
recovery_date: {recovery_timestamp}
original_published: "{published}"
---

{content}

---

**🔥 Drama Score:** {drama_score} | **Level:** {drama_level.upper()}

**👑 Celebrities Mentioned:** {', '.join(celebrity_display) if celebrity_display else 'Various'}

[📰 Read full article at {source_display}]({link})

---
*🔄 This post was recovered from JSON data on {current_time_display}. Originally processed from RSS feeds.*
"""

                # Write the file
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(frontmatter)

                    recovered_count += 1
                    logger.info(f"✅ Recovered ({i}/{len(entries)}): {filename}")

                except Exception as e:
                    logger.error(f"❌ Failed to write {filename}: {e}")

            logger.info(f"🎉 Recovery complete!")
            logger.info(f"✅ Successfully recovered: {recovered_count} posts")
            logger.info(f"⏭️ Skipped existing: {skipped_count} posts")
            logger.info(f"📁 Total entries processed: {len(entries)}")

            return recovered_count

        except FileNotFoundError:
            logger.error("❌ No data/gossip_data.json found to recover from")
            return 0
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in gossip_data.json: {e}")
            return 0
        except Exception as e:
            logger.error(f"❌ Error during recovery: {e}")
            return 0

if __name__ == "__main__":
    logger.info("🚀 Starting Post Recovery...")
    recovery = PostRecovery()
    recovered = recovery.recover_posts_from_json()

    if recovered > 0:
        logger.info(f"🎯 Success! Recovered {recovered} posts to _posts/ directory")
        logger.info("💡 Run 'bundle exec jekyll serve' to see your recovered posts!")
    else:
        logger.info("ℹ️ No posts were recovered. Check if data/gossip_data.json exists and contains entries.")
