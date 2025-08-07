#!/usr/bin/env python3
"""
Enhanced Gossip Room RSS Scraper - With Advanced Deduplication and Debug Logging
FIXED VERSION - Restores Jekyll post creation functionality
"""

import feedparser
import requests
import yaml
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
import time
import logging
import hashlib
from difflib import SequenceMatcher

# Setup dual logging - console and debug file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create debug logger that overwrites each run
debug_logger = logging.getLogger('scraper_debug')
debug_logger.setLevel(logging.DEBUG)
debug_handler = logging.FileHandler('scraper_debug.log', mode='w')
debug_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)

class GossipScraper:
    def __init__(self):
        self.base_path = Path('.')
        self.celebrities = self.load_celebrities()
        self.celebrity_names = self.extract_celebrity_names()
        self.processed_articles = self.load_processed_articles()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

        self.excluded_words = {
            'on the', 'of the', 'in the', 'to the', 'for the', 'with the',
            'and the', 'at the', 'by the', 'from the', 'who plays',
            'jesus christ', 'anderson and', 'new york', 'los angeles'
        }

        self.rss_feeds = {
            'tmz': {'url': 'https://www.tmz.com/rss.xml', 'weight': 3},
            'perez_hilton': {'url': 'https://perezhilton.com/feed/', 'weight': 3},
            'e_news': {'url': 'http://syndication.eonline.com/syndication/feeds/rssfeeds/topstories.xml', 'weight': 3},
            'us_weekly': {'url': 'https://www.usmagazine.com/feed/', 'weight': 3},
            'variety_alt': {'url': 'https://variety.com/feed/', 'weight': 2},
            'hollywood_reporter': {'url': 'https://www.hollywoodreporter.com/feed/', 'weight': 2},
            'deadline': {'url': 'https://deadline.com/feed/', 'weight': 2},
            'page_six': {'url': 'https://pagesix.com/feed/', 'weight': 2},
            'huffpost_entertainment': {'url': 'https://www.huffpost.com/section/entertainment/feed', 'weight': 2},
            'daily_mail': {'url': 'https://www.dailymail.co.uk/articles.rss', 'weight': 2},
            'rolling_stone': {'url': 'https://www.rollingstone.com/feed/', 'weight': 2},
            'billboard': {'url': 'https://www.billboard.com/feed/', 'weight': 2},
            'elle_alt': {'url': 'https://www.elle.com/rss/all.xml/', 'weight': 2},
            'vogue_alt': {'url': 'https://www.vogue.com/feed/rss', 'weight': 2},
            'pitchfork': {'url': 'https://pitchfork.com/rss/news/', 'weight': 1},
            'highsnobiety': {'url': 'https://www.highsnobiety.com/feed/', 'weight': 1},
            'sneaker_news': {'url': 'https://sneakernews.com/feed/', 'weight': 1},
            'espn': {'url': 'https://www.espn.com/espn/rss/news', 'weight': 1},
            'bbc_entertainment': {'url': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml', 'weight': 1},
        }

    def get_rejection_reason(self, title, content, link, article_id):
        """Determine why an article was rejected"""
        if not title or not link:
            return "Missing title or link"

        if article_id in self.processed_articles:
            return "Already processed (duplicate ID)"

        found_celebrities = self.contains_celebrity(title, content)
        if not found_celebrities:
            return "No celebrity matches found"

        return "Unknown rejection reason"

    def log_feed_results(self, feed_name, all_articles, accepted_articles, rejected_count):
        """Log detailed results for each feed"""
        debug_logger.info(f"\n{'='*60}")
        debug_logger.info(f"FEED: {feed_name.upper()}")
        debug_logger.info(f"Total articles fetched: {len(all_articles)}")
        debug_logger.info(f"Accepted: {len(accepted_articles)}, Rejected: {rejected_count}")
        debug_logger.info(f"{'='*60}")

        for i, article_info in enumerate(all_articles, 1):
            title = article_info['title'][:80] + "..." if len(article_info['title']) > 80 else article_info['title']
            status = "✅ ACCEPTED" if article_info['accepted'] else "❌ REJECTED"

            debug_logger.info(f"{i:2d}. {status} | {title}")

            if not article_info['accepted']:
                debug_logger.info(f"    └─ Reason: {article_info['rejection_reason']}")
            else:
                celebrities = article_info.get('celebrities', [])
                if celebrities:
                    debug_logger.info(f"    └─ Celebrities: {', '.join(celebrities[:3])}")

    def ensure_data_directory(self):
        Path('data').mkdir(exist_ok=True)

    def load_celebrities(self):
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {}

                if '_temperature_metadata' in data:
                    del data['_temperature_metadata']

                # Filter out brands
                people_only = {}
                for key, value in data.items():
                    category = value.get('category', '')
                    if category not in ['fashion_brand', 'brand']:
                        people_only[key] = value

                logger.info(f"Loaded {len(people_only)} people from celebrities.yml")
                return people_only
        except FileNotFoundError:
            logger.error("celebrities.yml not found!")
            return {}

    def extract_celebrity_names(self):
        names = []

        for celebrity_key, celebrity_data in self.celebrities.items():
            if celebrity_data.get('memorial', False):
                continue

            main_name = celebrity_key.replace('_', ' ')
            names.append(main_name.lower())

            variations = self.get_name_variations(celebrity_key, main_name)
            names.extend([v.lower() for v in variations])

        unique_names = sorted(list(set(names)))
        logger.info(f"Generated {len(unique_names)} searchable celebrity names")
        return unique_names

    def get_name_variations(self, celebrity_key, main_name):
        variations = []

        name_mappings = {
            'taylor_swift': ['taylor swift', 'swift', 't-swift'],
            'kanye_west': ['kanye west', 'kanye', 'ye'],
            'kim_kardashian': ['kim kardashian', 'kardashian'],
            'elon_musk': ['elon musk', 'musk'],
            'justin_bieber': ['justin bieber', 'bieber'],
            'drake': ['drake'],
            'beyonce': ['beyoncé', 'beyonce'],
            'ariana_grande': ['ariana grande', 'ariana'],
            'bad_bunny': ['bad bunny'],
            'pete_davidson': ['pete davidson'],
            'jenna_ortega': ['jenna ortega'],
            'sabrina_carpenter': ['sabrina carpenter'],
            'olivia_rodrigo': ['olivia rodrigo'],
            'pedro_pascal': ['pedro pascal'],
            'austin_butler': ['austin butler'],
            'anya_taylor_joy': ['anya taylor-joy', 'anya taylor joy'],
        }

        if celebrity_key in name_mappings:
            variations.extend(name_mappings[celebrity_key])

        return variations

    def load_processed_articles(self):
        self.ensure_data_directory()
        try:
            with open('data/processed_articles.json', 'r') as f:
                data = json.load(f)
                cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                cleaned = {k: v for k, v in data.items() 
                          if v.get('processed_date', '9999') > cutoff}
                logger.info(f"Loaded {len(cleaned)} recent processed articles")
                return cleaned
        except FileNotFoundError:
            return {}

    def normalize_title(self, title):
        """Normalize title for similarity comparison"""
        title = re.sub(r'[!?.:;,\'""]', '', title.lower())
        title = re.sub(r'\s+', ' ', title).strip()

        filler_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        words = title.split()
        filtered_words = [w for w in words if w not in filler_words]

        return ' '.join(filtered_words)

    def titles_are_similar(self, title1, title2, threshold=0.8):
        """Check if two titles are similar enough to be considered duplicates"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)

        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold

    def advanced_deduplication(self, posts):
        """Remove duplicate posts based on title similarity"""
        unique_posts = []
        seen_titles = []
        duplicates_removed = 0

        posts_sorted = sorted(posts, key=lambda x: x['drama_score'], reverse=True)

        for post in posts_sorted:
            current_title = post['title']
            is_duplicate = False

            for seen_title in seen_titles:
                if self.titles_are_similar(current_title, seen_title):
                    is_duplicate = True
                    duplicates_removed += 1
                    logger.debug(f"Duplicate found: '{current_title[:50]}...' similar to '{seen_title[:50]}...'")
                    break

            if not is_duplicate:
                unique_posts.append(post)
                seen_titles.append(current_title)

        logger.info(f"🔄 Deduplication: {len(posts)} → {len(unique_posts)} posts ({duplicates_removed} duplicates removed)")
        return unique_posts

    def save_processed_articles(self):
        self.ensure_data_directory()
        with open('data/processed_articles.json', 'w') as f:
            json.dump(self.processed_articles, f, indent=2)

    def clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def contains_celebrity(self, title, content):
        full_text = f"{title} {content}".lower()
        found_celebrities = []

        for celebrity_name in self.celebrity_names:
            if len(celebrity_name) < 4:
                continue
            pattern = r'\b' + re.escape(celebrity_name) + r'\b'
            if re.search(pattern, full_text):
                found_celebrities.append(celebrity_name)

        return found_celebrities

    def extract_celebrity_mentions(self, title, content, source_weight=1):
        text = f"{title} {content}".lower()
        mentions = {}

        for celebrity_key, celebrity_data in self.celebrities.items():
            if celebrity_data.get('memorial', False):
                continue

            main_name = celebrity_key.replace('_', ' ')
            name_variations = [main_name] + self.get_name_variations(celebrity_key, main_name)

            total_matches = 0
            for name in name_variations:
                if len(name) < 4:
                    continue
                pattern = r'\b' + re.escape(name.lower()) + r'\b'
                matches = len(re.findall(pattern, text))
                total_matches += matches

            if total_matches > 0:
                weighted_mentions = total_matches * source_weight
                mentions[celebrity_key] = weighted_mentions
                self.celebrity_mentions[celebrity_key] += weighted_mentions

        return mentions

    def detect_potential_celebrities(self, title, content):
        text = f"{title} {content}"

        patterns = [
            r'\bactor\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bactress\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bsinger\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\brapper\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bmusician\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.strip().lower()

                if (name in self.excluded_words or 
                    name.replace(' ', '_') in self.celebrities or
                    len(name) < 6):
                    continue

                self.potential_new_celebrities[name] += 1

    def create_clean_slug(self, title):
        """🎯 FIX: Create clean slug without trailing hyphens"""
        # Remove special characters except spaces and hyphens
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title).strip()
        # Replace multiple spaces with single hyphen
        slug = re.sub(r'\s+', '-', slug)
        # Replace multiple hyphens with single hyphen
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-').lower()
        # Limit length and ensure no trailing hyphen
        slug = slug[:50].rstrip('-')

        # Ensure we have a valid slug
        if not slug:
            slug = "post"

        return slug

    def create_blog_post(self, title, content, link, mentions, source):
        """🎯 FIXED: Create Jekyll blog post with clean filenames"""
        # Generate filename with clean slug
        date_str = datetime.now().strftime('%Y-%m-%d')
        slug = self.create_clean_slug(title)
        filename = f"{date_str}-{slug}.md"

        # Determine primary celebrity and drama level
        if not mentions:
            return None

        primary_celebrity = max(mentions.keys(), key=mentions.get)
        total_drama_score = sum(mentions.values())

        # Create tags
        tags = [primary_celebrity.replace('_', '-')]
        if primary_celebrity in self.celebrities:
            tags.extend(self.celebrities[primary_celebrity].get('tags', []))

        # Add source tag
        tags.append(f"source-{source}")

        # Determine drama level
        if total_drama_score >= 10:
            drama_level = "explosive"
        elif total_drama_score >= 5:
            drama_level = "hot"
        elif total_drama_score >= 2:
            drama_level = "rising"
        else:
            drama_level = "mild"

        tags.append(f"drama-{drama_level}")

        # Extract all string processing outside f-string to avoid backslash issues
        escaped_title = title.replace('"', '\\"')
        celebrity_names = ', '.join([k.replace('_', ' ').title() for k in mentions.keys()])
        source_title = source.replace('_', ' ').title()
        content_preview = content[:500] + '...' if len(content) > 500 else content

        # Create post content
        post_content = f"""---
layout: post
title: "{escaped_title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} +0000
categories: gossip
tags: {tags}
drama_score: {total_drama_score}
primary_celebrity: {primary_celebrity}
source: {source}
source_url: "{link}"
mentions: {dict(mentions)}
---

{content_preview}

**Drama Score:** {total_drama_score} | **Level:** {drama_level.upper()}

**Celebrities Mentioned:** {celebrity_names}

[Read full article at {source_title}]({link})

---
*This post was automatically generated from RSS feeds. Drama scores are calculated based on mention frequency and source reliability.*
"""

        return {
            'filename': filename,
            'content': post_content,
            'drama_score': total_drama_score,
            'mentions': mentions,
            'title': title  # Add for deduplication
        }

    def scrape_feed(self, feed_name, feed_info):
        try:
            logger.info(f"Scraping {feed_name}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; GossipRoomBot/1.0)'
            }

            response = requests.get(feed_info['url'], headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            articles_processed = 0
            articles_rejected = 0
            all_articles_info = []

            for entry in feed.entries[:20]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=48):
                        continue

                title = self.clean_text(entry.get('title', ''))
                content = self.clean_text(entry.get('summary', '') or entry.get('description', ''))
                link = entry.get('link', '')

                normalized_title = self.normalize_title(title)
                article_id = hashlib.md5(f"{normalized_title}{feed_name}".encode()).hexdigest()

                article_info = {
                    'title': title,
                    'link': link,
                    'accepted': False,
                    'rejection_reason': None,
                    'celebrities': []
                }

                rejection_reason = self.get_rejection_reason(title, content, link, article_id)

                if rejection_reason != "Unknown rejection reason":
                    article_info['rejection_reason'] = rejection_reason
                    articles_rejected += 1
                    all_articles_info.append(article_info)
                    continue

                found_celebrities = self.contains_celebrity(title, content)

                if not found_celebrities:
                    article_info['rejection_reason'] = "No celebrity matches found"
                    articles_rejected += 1
                    all_articles_info.append(article_info)
                    continue

                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])
                self.detect_potential_celebrities(title, content)

                if mentions:
                    # 🎯 FIXED: Create blog post with clean filename
                    post_data = self.create_blog_post(title, content, link, mentions, feed_name)
                    if post_data:
                        article_info['accepted'] = True
                        article_info['celebrities'] = found_celebrities
                        all_articles_info.append(article_info)

                        self.new_posts.append(post_data)
                        self.processed_articles[article_id] = {
                            'title': title,
                            'normalized_title': normalized_title,
                            'link': link,
                            'processed_date': datetime.now().isoformat()
                        }
                        articles_processed += 1

            self.log_feed_results(feed_name, all_articles_info, 
                                [a for a in all_articles_info if a['accepted']], 
                                articles_rejected)

            logger.info(f"✅ {feed_name}: {articles_processed} posts, {articles_rejected} rejected")
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Error scraping {feed_name}: {e}")
            debug_logger.error(f"❌ Error scraping {feed_name}: {e}")

    def update_celebrity_scores(self):
        for celebrity_key, mentions in self.celebrity_mentions.items():
            if celebrity_key in self.celebrities:
                current_score = self.celebrities[celebrity_key].get('drama_score', 50)
                new_score = min(100, int(current_score * 0.98 + mentions))
                self.celebrities[celebrity_key]['drama_score'] = new_score

                temp_change = new_score - current_score
                self.celebrities[celebrity_key]['temperature_change'] = temp_change

                if new_score >= 90:
                    status = 'explosive'
                elif new_score >= 70:
                    status = 'hot'
                elif new_score >= 50:
                    status = 'rising'
                elif new_score >= 30:
                    status = 'mild'
                else:
                    status = 'cooling'

                self.celebrities[celebrity_key]['status'] = status
                self.celebrities[celebrity_key]['last_temperature_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def check_auto_discovery(self):
        new_celebrities = {}

        for name, count in self.potential_new_celebrities.items():
            if count >= 3:
                celebrity_key = name.replace(' ', '_')
                new_celebrities[celebrity_key] = {
                    'category': 'unknown',
                    'discovery_date': datetime.now().strftime('%Y-%m-%d'),
                    'drama_score': min(70, count * 15),
                    'last_temperature_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'memorial': False,
                    'promotion_date': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'rising',
                    'temperature_change': count * 10
                }
                logger.info(f"🆕 Auto-discovered: {name}")

        return new_celebrities

    def save_data(self):
        self.ensure_data_directory()

        logger.info(f"📊 Before deduplication: {len(self.new_posts)} posts")

        # Apply advanced deduplication
        unique_posts = self.advanced_deduplication(self.new_posts)

        # Sort by drama score and limit
        unique_posts.sort(key=lambda x: (x['drama_score'], x.get('published', '')), reverse=True)
        final_posts = unique_posts[:50]

        # 🎯 RESTORED: Save Jekyll posts to _posts/ directory
        posts_dir = self.base_path / '_posts'
        posts_dir.mkdir(exist_ok=True)

        created_posts = 0
        for post in final_posts:
            post_path = posts_dir / post['filename']
            # Check if file already exists
            if not post_path.exists():
                with open(post_path, 'w', encoding='utf-8') as f:
                    f.write(post['content'])
                created_posts += 1
                logger.info(f"✅ Created: {post['filename']}")

        logger.info(f"📝 Created {created_posts} new Jekyll posts")

        # Save JSON data for debugging
        gossip_data = {
            'entries': final_posts,
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(final_posts),
            'sources_processed': len(self.rss_feeds),
            'deduplication_stats': {
                'raw_posts': len(self.new_posts),
                'after_dedup': len(unique_posts),
                'final_count': len(final_posts)
            },
            'celebrity_mentions': dict(self.celebrity_mentions),
            'top_celebrities': sorted(self.celebrity_mentions.items(), 
                                    key=lambda x: x[1], reverse=True)[:10]
        }

        with open('data/gossip_data.json', 'w') as f:
            json.dump(gossip_data, f, default=str, indent=2)

        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
            logger.info("✅ Updated celebrities.yml")
        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

        self.save_processed_articles()
        logger.info(f"💾 Final output: {len(final_posts)} unique posts")

    def run(self):
        debug_logger.info("🎭 STARTING ENHANCED GOSSIP ROOM SCRAPER")
        debug_logger.info(f"📋 Loaded {len(self.celebrities)} celebrities")
        debug_logger.info(f"🔍 Generated {len(self.celebrity_names)} searchable names")

        logger.info("🎭 Starting Enhanced Gossip Room scraper...")
        logger.info(f"📋 Loaded {len(self.celebrities)} celebrities")

        for feed_name, feed_info in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_info)

        self.update_celebrity_scores()

        new_celebrities = self.check_auto_discovery()
        if new_celebrities:
            self.celebrities.update(new_celebrities)
            logger.info(f"🆕 Added {len(new_celebrities)} new celebrities")

        self.save_data()

        logger.info("✨ Scraping complete!")
        debug_logger.info("✨ SCRAPING COMPLETE - Check scraper_debug.log for detailed analysis")

        if self.celebrity_mentions:
            top_mentions = sorted(self.celebrity_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("🔥 Top celebrity mentions:")
            for celebrity, count in top_mentions:
                logger.info(f"   {celebrity.replace('_', ' ').title()}: {count}")

if __name__ == "__main__":
    scraper = GossipScraper()
    scraper.run()
