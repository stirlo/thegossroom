#!/usr/bin/env python3
"""
Temperature-Based Gossip Room RSS Scraper
Limits to 33 hottest posts per day with intelligent queuing
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
import html
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

debug_logger = logging.getLogger('scraper_debug')
debug_logger.setLevel(logging.DEBUG)
debug_handler = logging.FileHandler('scraper_debug.log', mode='w')
debug_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)

class TemperatureBasedGossipScraper:
    def __init__(self):
        self.base_path = Path('.')
        self.celebrities = self.load_celebrities()
        self.celebrity_names = self.extract_celebrity_names()
        self.processed_articles = self.load_processed_articles()
        self.daily_queue = self.load_daily_queue()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

        # Temperature-based settings
        self.DAILY_POST_LIMIT = 33
        self.MIN_TEMPERATURE = 25
        self.ARCHIVE_DAYS = 30

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

    def ensure_data_directory(self):
        Path('data').mkdir(exist_ok=True)

    def load_daily_queue(self):
        """Load daily posting queue"""
        self.ensure_data_directory()
        try:
            with open('data/daily_queue.json', 'r') as f:
                queue_data = json.load(f)

                # Clean old entries
                today = datetime.now().strftime('%Y-%m-%d')
                if queue_data.get('date') != today:
                    return {'date': today, 'posted_count': 0, 'queue': []}

                return queue_data
        except FileNotFoundError:
            return {'date': datetime.now().strftime('%Y-%m-%d'), 'posted_count': 0, 'queue': []}

    def save_daily_queue(self):
        """Save daily posting queue"""
        self.ensure_data_directory()
        with open('data/daily_queue.json', 'w') as f:
            json.dump(self.daily_queue, f, indent=2, default=str)

    def calculate_post_temperature(self, post_data):
        """Calculate live temperature for a post"""
        base_score = post_data.get('drama_score', 0)

        # Celebrity temperature boost
        celebrity_boost = 0
        mentions = post_data.get('mentions', {})

        if mentions:
            total_celeb_temp = 0
            for celeb_key, mention_count in mentions.items():
                celeb_temp = self.celebrities.get(celeb_key, {}).get('drama_score', 0)
                total_celeb_temp += celeb_temp * mention_count

            celebrity_boost = total_celeb_temp / len(mentions)

        # Time decay (posts get cooler over time)
        post_time = datetime.now()  # New posts are hottest

        # Calculate final temperature
        temperature = base_score + (celebrity_boost * 0.6)
        return min(100, int(temperature))

    def archive_old_posts(self):
        """Archive posts older than 30 days"""
        posts_dir = self.base_path / '_posts'
        archive_dir = self.base_path / '_archive'
        archive_dir.mkdir(exist_ok=True)

        cutoff_date = datetime.now() - timedelta(days=self.ARCHIVE_DAYS)
        archived_count = 0

        for post_file in posts_dir.glob('*.md'):
            # Extract date from filename
            try:
                date_str = post_file.name[:10]  # YYYY-MM-DD
                post_date = datetime.strptime(date_str, '%Y-%m-%d')

                if post_date < cutoff_date:
                    # Move to archive
                    archive_path = archive_dir / post_file.name
                    shutil.move(str(post_file), str(archive_path))
                    archived_count += 1

            except (ValueError, IndexError):
                continue

        if archived_count > 0:
            logger.info(f"📦 Archived {archived_count} old posts")

    def get_daily_posts_published_today(self):
        """Count posts already published today"""
        posts_dir = self.base_path / '_posts'
        today = datetime.now().strftime('%Y-%m-%d')

        count = 0
        for post_file in posts_dir.glob(f'{today}-*.md'):
            count += 1

        return count

    def load_celebrities(self):
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {}

                # Filter out brands and memorial entries
                people_only = {}
                for key, value in data.items():
                    category = value.get('category', '')
                    memorial = value.get('memorial', False)
                    if category not in ['fashion_brand', 'brand'] and not memorial:
                        people_only[key] = value

                logger.info(f"Loaded {len(people_only)} active celebrities")
                return people_only
        except FileNotFoundError:
            logger.error("celebrities.yml not found!")
            return {}

    def extract_celebrity_names(self):
        names = []
        for celebrity_key, celebrity_data in self.celebrities.items():
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
            'taylor_swift': ['taylor swift', 'swift', 't-swift', 'tswift'],
            'kanye_west': ['kanye west', 'kanye', 'ye'],
            'kim_kardashian': ['kim kardashian', 'kardashian', 'kim k'],
            'elon_musk': ['elon musk', 'musk'],
            'justin_bieber': ['justin bieber', 'bieber'],
            'drake': ['drake'],
            'beyonce': ['beyoncé', 'beyonce', 'queen b'],
            'ariana_grande': ['ariana grande', 'ariana', 'ari'],
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
                # Keep only last 3 days for faster processing
                cutoff = (datetime.now() - timedelta(days=3)).isoformat()
                cleaned = {k: v for k, v in data.items() 
                          if v.get('processed_date', '9999') > cutoff}
                logger.info(f"Loaded {len(cleaned)} recent processed articles")
                return cleaned
        except FileNotFoundError:
            return {}

    def clean_text(self, text):
        """Comprehensive HTML entity cleaning"""
        if not text:
            return ""

        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)

        # Clean up remaining entities
        entity_replacements = {
            r'\[&#8230;\]': '...', r'\[&hellip;\]': '...', r'&#8230;': '...',
            r'&#8217;': "'", r'&#8216;': "'", r'&#8220;': '"', r'&#8221;': '"',
            r'&#8211;': '–', r'&#8212;': '—', r'&#38;': '&', r'&#39;': "'",
            r'&#34;': '"', r'&#60;': '<', r'&#62;': '>',
            r'&hellip;': '...', r'&rsquo;': "'", r'&lsquo;': "'",
            r'&rdquo;': '"', r'&ldquo;': '"', r'&ndash;': '–',
            r'&mdash;': '—', r'&amp;': '&', r'&quot;': '"',
            r'&apos;': "'", r'&lt;': '<', r'&gt;': '>'
        }

        for pattern, replacement in entity_replacements.items():
            text = re.sub(pattern, replacement, text)

        text = re.sub(r'&[a-zA-Z0-9#]+;?', ' ', text)
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

    def create_clean_slug(self, title):
        """Create clean slug for filename"""
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title).strip()
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-').lower()

        if not slug:
            slug = "post"
        return slug

    def create_blog_post(self, title, content, link, mentions, source):
        """Create Jekyll blog post with temperature calculation"""
        if not mentions:
            return None

        primary_celebrity = max(mentions.keys(), key=mentions.get)
        base_drama_score = sum(mentions.values())

        # Calculate temperature
        post_data = {
            'drama_score': base_drama_score,
            'mentions': mentions
        }
        temperature = self.calculate_post_temperature(post_data)

        # Only create posts above minimum temperature
        if temperature < self.MIN_TEMPERATURE:
            return None

        date_str = datetime.now().strftime('%Y-%m-%d')
        slug = self.create_clean_slug(title)
        filename = f"{date_str}-{slug}.md"

        # Create tags
        tags = [primary_celebrity.replace('_', '-')]
        if primary_celebrity in self.celebrities:
            tags.extend(self.celebrities[primary_celebrity].get('tags', []))
        tags.append(f"source-{source}")

        # Determine drama level based on temperature
        if temperature >= 80:
            drama_level = "nuclear"
        elif temperature >= 60:
            drama_level = "explosive"
        elif temperature >= 40:
            drama_level = "hot"
        elif temperature >= 25:
            drama_level = "rising"
        else:
            drama_level = "mild"

        tags.append(f"drama-{drama_level}")

        escaped_title = title.replace('"', '\\"')
        celebrity_names = ', '.join([k.replace('_', ' ').title() for k in mentions.keys()])
        source_title = source.replace('_', ' ').title()
        content_preview = content[:400] + '...' if len(content) > 400 else content

        post_content = f"""---
layout: post
title: "{escaped_title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} +0000
categories: gossip
tags: {tags}
drama_score: {base_drama_score}
temperature: {temperature}
primary_celebrity: {primary_celebrity}
source: {source}
source_url: "{link}"
mentions: {dict(mentions)}
publish: true
---

{content_preview}

**🌡️ Temperature:** {temperature}° | **Drama Score:** {base_drama_score} | **Level:** {drama_level.upper()}

**Celebrities Mentioned:** {celebrity_names}

[Read full article at {source_title}]({link})

---
*This post was automatically generated from RSS feeds. Temperature calculated from celebrity drama scores and mention frequency.*
"""

        return {
            'filename': filename,
            'content': post_content,
            'drama_score': base_drama_score,
            'temperature': temperature,
            'mentions': mentions,
            'title': title,
            'primary_celebrity': primary_celebrity,
            'created_at': datetime.now().isoformat()
        }

    def scrape_feed(self, feed_name, feed_info):
        try:
            logger.info(f"Scraping {feed_name}...")

            headers = {'User-Agent': 'Mozilla/5.0 (compatible; GossipRoomBot/1.0)'}
            response = requests.get(feed_info['url'], headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            articles_processed = 0

            for entry in feed.entries[:15]:  # Reduced from 20
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=24):  # Only last 24 hours
                        continue

                title = self.clean_text(entry.get('title', ''))
                content = self.clean_text(entry.get('summary', '') or entry.get('description', ''))
                link = entry.get('link', '')

                if not title or not link:
                    continue

                # Quick duplicate check
                normalized_title = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
                article_id = hashlib.md5(f"{normalized_title}{feed_name}".encode()).hexdigest()

                if article_id in self.processed_articles:
                    continue

                found_celebrities = self.contains_celebrity(title, content)
                if not found_celebrities:
                    continue

                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])
                if mentions:
                    post_data = self.create_blog_post(title, content, link, mentions, feed_name)
                    if post_data:
                        self.new_posts.append(post_data)
                        self.processed_articles[article_id] = {
                            'title': title,
                            'link': link,
                            'processed_date': datetime.now().isoformat()
                        }
                        articles_processed += 1

            logger.info(f"✅ {feed_name}: {articles_processed} hot posts found")
            time.sleep(0.3)  # Reduced delay

        except Exception as e:
            logger.error(f"❌ Error scraping {feed_name}: {e}")

    def update_celebrity_scores(self):
        """Update celebrity drama scores based on mentions"""
        for celebrity_key, mentions in self.celebrity_mentions.items():
            if celebrity_key in self.celebrities:
                current_score = self.celebrities[celebrity_key].get('drama_score', 50)

                # More aggressive score updates
                boost = min(mentions * 2, 20)  # Max boost of 20 per run
                new_score = min(100, int(current_score * 0.95 + boost))

                self.celebrities[celebrity_key]['drama_score'] = new_score
                self.celebrities[celebrity_key]['temperature_change'] = new_score - current_score

                # Update status
                if new_score >= 85:
                    status = 'nuclear'
                elif new_score >= 70:
                    status = 'explosive'
                elif new_score >= 50:
                    status = 'hot'
                elif new_score >= 30:
                    status = 'rising'
                else:
                    status = 'cooling'

                self.celebrities[celebrity_key]['status'] = status
                self.celebrities[celebrity_key]['last_temperature_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def manage_daily_posts(self):
        """Manage daily post limit and queue system"""
        posts_published_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_published_today

        logger.info(f"📊 Daily Status: {posts_published_today}/{self.DAILY_POST_LIMIT} posts published")

        if remaining_slots <= 0:
            logger.info("🚫 Daily limit reached - queuing posts for tomorrow")
            return []

        # Sort all posts by temperature
        all_posts = sorted(self.new_posts, key=lambda x: x['temperature'], reverse=True)

        # Take only the hottest posts that fit in remaining slots
        posts_to_publish = all_posts[:remaining_slots]

        # Queue the rest for later
        queued_posts = all_posts[remaining_slots:]
        if queued_posts:
            logger.info(f"📋 Queuing {len(queued_posts)} posts for later")
            self.daily_queue['queue'].extend(queued_posts)

        return posts_to_publish

    def save_data(self):
        """Save data with temperature-based filtering"""
        self.ensure_data_directory()

        logger.info(f"🌡️ Found {len(self.new_posts)} posts above {self.MIN_TEMPERATURE}° temperature")

        # Archive old posts first
        self.archive_old_posts()

        # Manage daily posting limits
        posts_to_publish = self.manage_daily_posts()

        # Save Jekyll posts
        posts_dir = self.base_path / '_posts'
        posts_dir.mkdir(exist_ok=True)

        created_posts = 0
        for post in posts_to_publish:
            post_path = posts_dir / post['filename']
            if not post_path.exists():
                with open(post_path, 'w', encoding='utf-8') as f:
                    f.write(post['content'])
                created_posts += 1
                logger.info(f"🔥 Published: {post['title'][:50]}... (🌡️{post['temperature']}°)")

        logger.info(f"📝 Published {created_posts} new posts")

        # Save updated celebrity data
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
            logger.info("✅ Updated celebrities.yml")
        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

        # Save processed articles
        with open('data/processed_articles.json', 'w') as f:
            json.dump(self.processed_articles, f, indent=2)

        # Save daily queue
        self.save_daily_queue()

        # Save temperature analytics
        temperature_data = {
            'last_updated': datetime.now().isoformat(),
            'posts_published_today': created_posts,
            'posts_queued': len(self.daily_queue.get('queue', [])),
            'hottest_celebrities': sorted(self.celebrity_mentions.items(), 
                                        key=lambda x: x[1], reverse=True)[:10],
            'temperature_distribution': {
                'nuclear': len([p for p in self.new_posts if p['temperature'] >= 80]),
                'explosive': len([p for p in self.new_posts if 60 <= p['temperature'] < 80]),
                'hot': len([p for p in self.new_posts if 40 <= p['temperature'] < 60]),
                'rising': len([p for p in self.new_posts if 25 <= p['temperature'] < 40])
            }
        }

        with open('data/temperature_analytics.json', 'w') as f:
            json.dump(temperature_data, f, indent=2, default=str)

    def run(self):
        """Main temperature-based scraping process"""
        logger.info("🌡️ Starting Temperature-Based Gossip Scraper...")
        logger.info(f"📊 Daily limit: {self.DAILY_POST_LIMIT} posts, Min temp: {self.MIN_TEMPERATURE}°")

        for feed_name, feed_info in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_info)

        self.update_celebrity_scores()
        self.save_data()

        logger.info("✨ Temperature-based scraping complete!")

        if self.celebrity_mentions:
            top_mentions = sorted(self.celebrity_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("🔥 Hottest celebrities this run:")
            for celebrity, count in top_mentions:
                temp = self.celebrities.get(celebrity, {}).get('drama_score', 0)
                logger.info(f"   {celebrity.replace('_', ' ').title()}: {count} mentions (🌡️{temp}°)")

if __name__ == "__main__":
    scraper = TemperatureBasedGossipScraper()
    scraper.run()
