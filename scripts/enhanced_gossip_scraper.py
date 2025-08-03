#!/usr/bin/env python3
"""
Enhanced Gossip Room RSS Scraper - Fixed Version
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GossipScraper:
    def __init__(self):
        self.base_path = Path('.')
        self.celebrities = self.load_celebrities()
        self.celebrity_names = self.extract_celebrity_names()
        self.processed_articles = self.load_processed_articles()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

        # Common words to exclude from auto-discovery
        self.excluded_words = {
            'on the', 'of the', 'in the', 'to the', 'for the', 'with the',
            'and the', 'at the', 'by the', 'from the', 'who plays',
            'jesus christ', 'anderson and', 'new york', 'los angeles',
            'united states', 'new jersey', 'south korea', 'north korea'
        }

        # Working RSS feeds only
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
            'nine_celebrity': {'url': 'http://www.9celebrity.com/feed/', 'weight': 1},
            'highsnobiety': {'url': 'https://www.highsnobiety.com/feed/', 'weight': 1},
            'sneaker_news': {'url': 'https://sneakernews.com/feed/', 'weight': 1},
            'espn': {'url': 'https://www.espn.com/espn/rss/news', 'weight': 1},
            'cnn_entertainment': {'url': 'http://rss.cnn.com/rss/edition.rss', 'weight': 1},
            'bbc_entertainment': {'url': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml', 'weight': 1},
        }

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

                # Filter out brands and focus on people
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

            # Add specific variations for key celebrities
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
                # Clean old entries (older than 7 days)
                cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                cleaned = {k: v for k, v in data.items() 
                          if v.get('processed_date', '9999') > cutoff}
                logger.info(f"Loaded {len(cleaned)} recent processed articles")
                return cleaned
        except FileNotFoundError:
            return {}

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
            if len(celebrity_name) < 4:  # Skip very short names
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
                if len(name) < 4:  # Skip very short names
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

        # More restrictive patterns
        patterns = [
            r'\bactor\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bactress\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bsinger\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\brapper\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bmusician\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\bcelebrity\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.strip().lower()

                # Skip if in excluded words or already tracked
                if (name in self.excluded_words or 
                    name.replace(' ', '_') in self.celebrities or
                    len(name) < 6):
                    continue

                self.potential_new_celebrities[name] += 1

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

            for entry in feed.entries[:20]:  # Limit entries per feed
                # Check recency
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=48):
                        continue

                title = self.clean_text(entry.get('title', ''))
                content = self.clean_text(entry.get('summary', '') or entry.get('description', ''))
                link = entry.get('link', '')

                if not title or not link:
                    continue

                # Generate unique ID
                article_id = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                if article_id in self.processed_articles:
                    continue

                # Check for celebrity mentions
                found_celebrities = self.contains_celebrity(title, content)

                if not found_celebrities:
                    articles_rejected += 1
                    continue

                # Extract mentions
                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])

                # Auto-discovery
                self.detect_potential_celebrities(title, content)

                if mentions:
                    entry_data = {
                        'id': article_id,
                        'title': title,
                        'content': content[:300] + ('...' if len(content) > 300 else ''),
                        'link': link,
                        'published': entry.get('published', ''),
                        'source': feed_name,
                        'weight': feed_info['weight'],
                        'mentions': mentions,
                        'celebrities': found_celebrities[:3],  # Limit to top 3
                        'drama_score': sum(mentions.values())
                    }

                    self.new_posts.append(entry_data)
                    self.processed_articles[article_id] = {
                        'title': title,
                        'link': link,
                        'processed_date': datetime.now().isoformat()
                    }
                    articles_processed += 1

            logger.info(f"✅ {feed_name}: {articles_processed} posts, {articles_rejected} rejected")
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Error scraping {feed_name}: {e}")

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
            if count >= 3:  # Threshold
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

        # Remove duplicates by ID
        unique_posts = {}
        for post in self.new_posts:
            unique_posts[post['id']] = post

        final_posts = list(unique_posts.values())
        final_posts.sort(key=lambda x: (x['drama_score'], x.get('published', '')), reverse=True)

        # Limit to reasonable number
        final_posts = final_posts[:100]

        gossip_data = {
            'entries': final_posts,
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(final_posts),
            'sources_processed': len([f for f in self.rss_feeds.keys()]),
            'celebrity_mentions': dict(self.celebrity_mentions),
            'stats': {
                'total_scraped': len(self.new_posts),
                'after_dedup': len(final_posts),
                'top_celebrities': sorted(self.celebrity_mentions.items(), 
                                        key=lambda x: x[1], reverse=True)[:10]
            }
        }

        with open('data/gossip_data.json', 'w') as f:
            json.dump(gossip_data, f, default=str, indent=2)

        # Save updated celebrities
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
            logger.info("✅ Updated celebrities.yml")
        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

        self.save_processed_articles()
        logger.info(f"💾 Saved {len(final_posts)} unique posts (from {len(self.new_posts)} scraped)")

    def run(self):
        logger.info("🎭 Starting Enhanced Gossip Room scraper...")
        logger.info(f"📋 Loaded {len(self.celebrities)} celebrities")
        logger.info(f"🔍 Tracking {len(self.celebrity_names)} searchable names")

        for feed_name, feed_info in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_info)

        logger.info(f"📊 Raw posts collected: {len(self.new_posts)}")

        self.update_celebrity_scores()

        new_celebrities = self.check_auto_discovery()
        if new_celebrities:
            self.celebrities.update(new_celebrities)
            logger.info(f"🆕 Added {len(new_celebrities)} new celebrities")

        self.save_data()

        logger.info("✨ Scraping complete!")

        if self.celebrity_mentions:
            top_mentions = sorted(self.celebrity_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("🔥 Top celebrity mentions:")
            for celebrity, count in top_mentions:
                logger.info(f"   {celebrity.replace('_', ' ').title()}: {count}")

if __name__ == "__main__":
    scraper = GossipScraper()
    scraper.run()
