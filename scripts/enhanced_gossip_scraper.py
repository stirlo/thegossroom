#!/usr/bin/env python3
"""
Enhanced Gossip Room RSS Scraper
Uses celebrities.yml as the single source of truth for celebrity tracking
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
from urllib.parse import urlparse
import logging
import hashlib

# Setup logging
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

        # Comprehensive RSS feeds with weights
        self.rss_feeds = {
            # TIER 1: Premium Celebrity Gossip (Weight 3)
            'tmz': {'url': 'https://www.tmz.com/rss.xml', 'weight': 3},
            'perez_hilton': {'url': 'https://perezhilton.com/feed/', 'weight': 3},
            'just_jared': {'url': 'https://www.justjared.com/rss.xml', 'weight': 3},
            'e_news': {'url': 'http://syndication.eonline.com/syndication/feeds/rssfeeds/topstories.xml', 'weight': 3},
            'people_celebrities': {'url': 'https://people.com/tag/celebrities/rss', 'weight': 3},
            'people_all': {'url': 'https://people.com/feeds/all.rss', 'weight': 3},
            'entertainment_tonight': {'url': 'https://www.etonline.com/feed', 'weight': 3},
            'us_magazine_celebrity': {'url': 'https://www.usmagazine.com/celebrity-news/feed/', 'weight': 3},
            'us_weekly': {'url': 'https://www.usmagazine.com/feed/', 'weight': 3},

            # TIER 2: Major Entertainment News (Weight 2)
            'entertainment_weekly': {'url': 'http://feeds.feedburner.com/entertainmentweekly/latest', 'weight': 2},
            'variety': {'url': 'https://variety.com/v/feed/', 'weight': 2},
            'variety_alt': {'url': 'https://variety.com/feed/', 'weight': 2},
            'hollywood_reporter': {'url': 'https://www.hollywoodreporter.com/feed/', 'weight': 2},
            'deadline': {'url': 'https://deadline.com/feed/', 'weight': 2},
            'page_six': {'url': 'https://pagesix.com/feed/', 'weight': 2},
            'hello_magazine': {'url': 'https://www.hellomagazine.com/rss/showbiz.rss', 'weight': 2},
            'huffpost_entertainment': {'url': 'https://www.huffpost.com/section/entertainment/feed', 'weight': 2},
            'daily_mail': {'url': 'https://www.dailymail.co.uk/articles.rss', 'weight': 2},
            'metro_showbiz': {'url': 'https://metro.co.uk/tag/showbiz/rss/', 'weight': 2},

            # TIER 2: Music Sources (Weight 2)
            'rolling_stone': {'url': 'https://www.rollingstone.com/feed/', 'weight': 2},
            'billboard': {'url': 'https://www.billboard.com/feed/', 'weight': 2},

            # TIER 2: Fashion & Lifestyle (Weight 2)
            'elle': {'url': 'https://www.elle.com/rss/everything/', 'weight': 2},
            'elle_alt': {'url': 'https://www.elle.com/rss/all.xml/', 'weight': 2},
            'vogue': {'url': 'https://www.vogue.com/rss/index.xml', 'weight': 2},
            'vogue_alt': {'url': 'https://www.vogue.com/feed/rss', 'weight': 2},
            'harpers_bazaar': {'url': 'https://www.harpersbazaar.com/rss', 'weight': 2},
            'gq': {'url': 'https://www.gq.com/rss/all', 'weight': 2},
            'esquire': {'url': 'https://www.esquire.com/rss/', 'weight': 2},

            # TIER 3: Specialty Sources (Weight 1)
            'pitchfork': {'url': 'https://pitchfork.com/rss/news/', 'weight': 1},
            'newscelebrity': {'url': 'https://www.newsclebrity.com/feed/', 'weight': 1},
            'nine_celebrity': {'url': 'http://www.9celebrity.com/feed/', 'weight': 1},
            'highsnobiety': {'url': 'https://www.highsnobiety.com/feed/', 'weight': 1},
            'hypebeast': {'url': 'https://hypebeast.com/rss', 'weight': 1},
            'sneaker_news': {'url': 'https://sneakernews.com/feed/', 'weight': 1},

            # TIER 3: Sports/General (Weight 1)
            'espn': {'url': 'https://www.espn.com/espn/rss/news', 'weight': 1},
            'cnn_entertainment': {'url': 'http://rss.cnn.com/rss/edition.rss', 'weight': 1},
            'bbc_entertainment': {'url': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml', 'weight': 1},
        }

    def ensure_data_directory(self):
        """Ensure data directory exists"""
        Path('data').mkdir(exist_ok=True)

    def load_celebrities(self):
        """Load celebrity database from celebrities.yml"""
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    logger.warning("celebrities.yml is empty")
                    return {}

                # Remove metadata if it exists
                if '_temperature_metadata' in data:
                    del data['_temperature_metadata']

                logger.info(f"Loaded {len(data)} celebrities from celebrities.yml")
                return data
        except FileNotFoundError:
            logger.error("celebrities.yml not found in _data/ directory!")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing celebrities.yml: {e}")
            return {}

    def extract_celebrity_names(self):
        """Extract searchable names from celebrity data"""
        names = []

        for celebrity_key, celebrity_data in self.celebrities.items():
            # Skip memorial celebrities that are inactive
            if celebrity_data.get('memorial', False):
                continue

            # Add the main name (key converted from underscore to space)
            main_name = celebrity_key.replace('_', ' ')
            names.append(main_name.lower())

            # Add name variations for better matching
            variations = self.get_name_variations(celebrity_key, main_name)
            names.extend([v.lower() for v in variations])

        # Remove duplicates and sort
        unique_names = sorted(list(set(names)))
        logger.info(f"Generated {len(unique_names)} searchable celebrity names")
        return unique_names

    def get_name_variations(self, celebrity_key, main_name):
        """Generate name variations for better matching"""
        variations = []

        # Common name mappings for better detection
        name_mappings = {
            'taylor_swift': ['taylor swift', 'swift', 't-swift', 'tswift'],
            'kanye_west': ['kanye west', 'kanye', 'ye', 'yeezy'],
            'kim_kardashian': ['kim kardashian', 'kardashian', 'kim k'],
            'elon_musk': ['elon musk', 'musk', 'elon'],
            'justin_bieber': ['justin bieber', 'bieber', 'jb'],
            'drake': ['drake', 'aubrey graham'],
            'beyonce': ['beyoncé', 'beyonce', 'queen b'],
            'ariana_grande': ['ariana grande', 'ariana', 'ari'],
            'bad_bunny': ['bad bunny', 'benito'],
            'pete_davidson': ['pete davidson', 'pete'],
            'jenna_ortega': ['jenna ortega', 'jenna'],
            'sabrina_carpenter': ['sabrina carpenter', 'sabrina'],
            'olivia_rodrigo': ['olivia rodrigo', 'olivia'],
            'pedro_pascal': ['pedro pascal', 'pedro'],
            'austin_butler': ['austin butler', 'austin'],
            'anya_taylor_joy': ['anya taylor-joy', 'anya taylor joy', 'anya'],
        }

        if celebrity_key in name_mappings:
            variations.extend(name_mappings[celebrity_key])
        else:
            # Generate basic variations
            parts = main_name.split()
            if len(parts) == 2:
                # Add first name only and last name only
                variations.extend(parts)
            elif len(parts) > 2:
                # For longer names, add first and last
                variations.extend([parts[0], parts[-1]])

        return variations

    def load_processed_articles(self):
        """Load processed articles to avoid duplicates"""
        self.ensure_data_directory()
        try:
            with open('data/processed_articles.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_processed_articles(self):
        """Save processed articles"""
        self.ensure_data_directory()
        with open('data/processed_articles.json', 'w') as f:
            json.dump(self.processed_articles, f)

    def clean_text(self, text):
        """Clean and normalize text for processing"""
        if not text:
            return ""
        # Remove HTML tags, normalize whitespace
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def contains_celebrity(self, title, content):
        """Check if content mentions any tracked celebrities"""
        full_text = f"{title} {content}".lower()
        found_celebrities = []

        for celebrity_name in self.celebrity_names:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(celebrity_name) + r'\b'
            if re.search(pattern, full_text):
                found_celebrities.append(celebrity_name)

        return found_celebrities

    def extract_celebrity_mentions(self, title, content, source_weight=1):
        """Extract and weight celebrity mentions"""
        text = f"{title} {content}".lower()
        mentions = {}

        for celebrity_key, celebrity_data in self.celebrities.items():
            # Skip memorial celebrities
            if celebrity_data.get('memorial', False):
                continue

            # Get all name variations for this celebrity
            main_name = celebrity_key.replace('_', ' ')
            name_variations = [main_name] + self.get_name_variations(celebrity_key, main_name)

            total_matches = 0
            for name in name_variations:
                pattern = r'\b' + re.escape(name.lower()) + r'\b'
                matches = len(re.findall(pattern, text))
                total_matches += matches

            if total_matches > 0:
                # Weight the mentions by source importance and current celebrity temperature
                base_weight = total_matches * source_weight
                celebrity_temp = celebrity_data.get('drama_score', 50)
                temp_multiplier = 1 + (celebrity_temp / 100)  # Higher temp = higher weight

                weighted_mentions = int(base_weight * temp_multiplier)
                mentions[celebrity_key] = weighted_mentions

                # Track for analytics
                self.celebrity_mentions[celebrity_key] += weighted_mentions

        return mentions

    def detect_potential_celebrities(self, title, content):
        """Auto-discovery of potential new celebrities"""
        text = f"{title} {content}"

        # Look for patterns that suggest celebrity names
        patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b(?=.*(?:actor|actress|singer|rapper|celebrity|star|musician|artist))',
            r'\b(?:actor|actress|singer|rapper|celebrity|star|musician|artist)\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:performs|releases|announces|arrested|married|divorced)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                # Check if it's not already in our database
                name_key = name.lower().replace(' ', '_')
                if name_key not in self.celebrities and len(name) > 5:
                    self.potential_new_celebrities[name] += 1

    def scrape_feed(self, feed_name, feed_info):
        """Scrape individual RSS feed"""
        try:
            logger.info(f"Scraping {feed_name}...")

            # Add user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; GossipRoomBot/1.0; +https://github.com/stirlo/thegossroom)'
            }

            response = requests.get(feed_info['url'], headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"Feed {feed_name} has parsing issues")

            articles_processed = 0
            articles_rejected = 0

            for entry in feed.entries[:25]:  # Process more entries
                # Check if article is recent (last 48 hours)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(days=2):
                        continue

                title = self.clean_text(entry.get('title', ''))
                content = self.clean_text(entry.get('summary', '') or entry.get('description', ''))
                link = entry.get('link', '')

                if not title or not link:
                    continue

                # Generate unique article ID
                article_id = hashlib.md5(link.encode()).hexdigest()
                if article_id in self.processed_articles:
                    continue

                # Check for celebrity mentions
                found_celebrities = self.contains_celebrity(title, content)

                if not found_celebrities:
                    articles_rejected += 1
                    continue

                # Extract detailed celebrity mentions
                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])

                # Auto-discovery
                self.detect_potential_celebrities(title, content)

                if mentions:
                    # Create entry data
                    entry_data = {
                        'id': article_id,
                        'title': title,
                        'content': content[:500] + ('...' if len(content) > 500 else ''),
                        'link': link,
                        'published': entry.get('published', ''),
                        'source': feed_name,
                        'weight': feed_info['weight'],
                        'mentions': mentions,
                        'celebrities': found_celebrities,
                        'drama_score': sum(mentions.values())
                    }

                    self.new_posts.append(entry_data)
                    self.processed_articles[article_id] = {
                        'title': title,
                        'link': link,
                        'published': entry.get('published', ''),
                        'processed_date': datetime.now().isoformat()
                    }
                    articles_processed += 1

            logger.info(f"✅ {feed_name}: {articles_processed} celebrity posts, {articles_rejected} rejected")
            time.sleep(1)  # Be nice to servers

        except Exception as e:
            logger.error(f"❌ Error scraping {feed_name}: {e}")

    def update_celebrity_scores(self):
        """Update celebrity drama scores based on recent mentions"""
        for celebrity_key, mentions in self.celebrity_mentions.items():
            if celebrity_key in self.celebrities:
                current_score = self.celebrities[celebrity_key].get('drama_score', 50)
                # Decay old score slightly and add new mentions
                new_score = int(current_score * 0.98 + mentions)
                self.celebrities[celebrity_key]['drama_score'] = new_score

                # Update temperature change
                old_temp = current_score
                temp_change = new_score - old_temp
                self.celebrities[celebrity_key]['temperature_change'] = temp_change

                # Update status based on score
                if new_score >= 90:
                    self.celebrities[celebrity_key]['status'] = 'explosive'
                elif new_score >= 70:
                    self.celebrities[celebrity_key]['status'] = 'hot'
                elif new_score >= 50:
                    self.celebrities[celebrity_key]['status'] = 'rising'
                elif new_score >= 30:
                    self.celebrities[celebrity_key]['status'] = 'mild'
                else:
                    self.celebrities[celebrity_key]['status'] = 'cooling'

                # Update last temperature update
                self.celebrities[celebrity_key]['last_temperature_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def check_auto_discovery(self):
        """Check if any potential celebrities should be added"""
        new_celebrities = {}

        for name, count in self.potential_new_celebrities.items():
            # Threshold: 3+ mentions in this scrape cycle
            if count >= 3:
                celebrity_key = name.lower().replace(' ', '_')
                new_celebrities[celebrity_key] = {
                    'category': 'unknown',
                    'discovery_date': datetime.now().strftime('%Y-%m-%d'),
                    'drama_score': count * 15,  # Initial score
                    'last_temperature_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'memorial': False,
                    'promotion_date': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'rising',
                    'temperature_change': count * 10
                }
                logger.info(f"🆕 Auto-discovered potential celebrity: {name}")

        return new_celebrities

    def save_data(self):
        """Save all updated data"""
        self.ensure_data_directory()

        # Sort posts by drama score and recency
        self.new_posts.sort(key=lambda x: (x['drama_score'], x.get('published', '')), reverse=True)

        # Save main gossip data
        gossip_data = {
            'entries': self.new_posts,
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(self.new_posts),
            'sources_processed': len(self.rss_feeds),
            'celebrity_mentions': dict(self.celebrity_mentions),
            'potential_new_celebrities': dict(self.potential_new_celebrities)
        }

        with open('data/gossip_data.json', 'w') as f:
            json.dump(gossip_data, f, default=str, indent=2)

        # Save updated celebrities back to YAML
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
            logger.info("✅ Updated celebrities.yml with new scores")
        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

        # Save processed articles
        self.save_processed_articles()

        logger.info(f"💾 Saved {len(self.new_posts)} new posts")

    def run(self):
        """Main scraping process"""
        logger.info("🎭 Starting Enhanced Gossip Room scraper...")
        logger.info(f"📋 Loaded {len(self.celebrities)} celebrities from YAML")
        logger.info(f"🔍 Tracking {len(self.celebrity_names)} searchable names")

        # Scrape all feeds
        for feed_name, feed_info in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_info)

        # Update celebrity scores
        self.update_celebrity_scores()

        # Check for auto-discoveries
        new_celebrities = self.check_auto_discovery()
        if new_celebrities:
            self.celebrities.update(new_celebrities)
            logger.info(f"🆕 Added {len(new_celebrities)} new celebrities via auto-discovery")

        # Save all data
        self.save_data()

        logger.info("✨ Gossip scraping complete!")
        logger.info(f"📊 Total mentions tracked: {sum(self.celebrity_mentions.values())}")
        logger.info(f"📝 New posts created: {len(self.new_posts)}")

        # Show top mentions
        if self.celebrity_mentions:
            top_mentions = sorted(self.celebrity_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("🔥 Top celebrity mentions this run:")
            for celebrity, count in top_mentions:
                logger.info(f"   {celebrity.replace('_', ' ').title()}: {count}")

if __name__ == "__main__":
    scraper = GossipScraper()
    scraper.run()