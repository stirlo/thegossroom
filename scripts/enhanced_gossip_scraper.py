#!/usr/bin/env python3
"""
Enhanced Gossip Room RSS Scraper
Improved version with better celebrity detection, auto-discovery, and drama scoring
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedGossipScraper:
    def __init__(self):
        self.base_path = Path('.')
        self.celebrities = self.load_celebrities()
        self.rss_feeds = self.load_rss_feeds()
        self.drama_data = self.load_drama_data()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

    def load_celebrities(self):
        """Load celebrity database"""
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("celebrities.yml not found")
            return {}

    def load_rss_feeds(self):
        """RSS feeds with weights for importance"""
        return {
            # High-weight celebrity sources
            'tmz': {'url': 'https://www.tmz.com/rss.xml', 'weight': 3},
            'people': {'url': 'https://people.com/feeds/all.rss', 'weight': 3},
            'entertainment_tonight': {'url': 'https://www.etonline.com/feed', 'weight': 3},
            'e_news': {'url': 'https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml', 'weight': 3},

            # Medium-weight sources
            'hollywood_reporter': {'url': 'https://www.hollywoodreporter.com/feed/', 'weight': 2},
            'variety': {'url': 'https://variety.com/feed/', 'weight': 2},
            'deadline': {'url': 'https://deadline.com/feed/', 'weight': 2},
            'page_six': {'url': 'https://pagesix.com/feed/', 'weight': 2},
            'us_weekly': {'url': 'https://www.usmagazine.com/feed/', 'weight': 2},

            # Music sources
            'rolling_stone': {'url': 'https://www.rollingstone.com/feed/', 'weight': 2},
            'billboard': {'url': 'https://www.billboard.com/feed/', 'weight': 2},
            'pitchfork': {'url': 'https://pitchfork.com/rss/news/', 'weight': 1},

            # Fashion/lifestyle
            'vogue': {'url': 'https://www.vogue.com/feed/rss', 'weight': 1},
            'elle': {'url': 'https://www.elle.com/rss/all.xml/', 'weight': 1},

            # Sports entertainment
            'espn': {'url': 'https://www.espn.com/espn/rss/news', 'weight': 1},

            # Tech/business (for Elon, etc.)
            'techcrunch': {'url': 'https://techcrunch.com/feed/', 'weight': 1},

            # General news (for political figures)
            'cnn_entertainment': {'url': 'http://rss.cnn.com/rss/edition.rss', 'weight': 1},
            'bbc_entertainment': {'url': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml', 'weight': 1},
        }

    def load_drama_data(self):
        """Load existing drama tracking data"""
        try:
            with open(self.base_path / '_data' / 'drama_tracking.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {'last_update': None, 'daily_mentions': {}, 'weekly_trends': {}}

    def clean_text(self, text):
        """Clean and normalize text for processing"""
        if not text:
            return ""
        # Remove HTML tags, normalize whitespace
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_celebrity_mentions(self, title, content, source_weight=1):
        """Enhanced celebrity detection with context awareness"""
        text = f"{title} {content}".lower()
        mentions = {}

        for celebrity_key, celebrity_data in self.celebrities.items():
            # Skip memorial celebrities that have expired
            if celebrity_data.get('status') == 'memorial':
                if self.is_memorial_expired(celebrity_data):
                    continue

            # Create multiple name variations for better matching
            name_variations = self.get_name_variations(celebrity_key)

            for name in name_variations:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(name.lower()) + r'\b'
                matches = len(re.findall(pattern, text))

                if matches > 0:
                    # Weight the mentions by source importance
                    weighted_mentions = matches * source_weight
                    mentions[celebrity_key] = mentions.get(celebrity_key, 0) + weighted_mentions

                    # Track for drama scoring
                    self.celebrity_mentions[celebrity_key] += weighted_mentions

        return mentions

    def get_name_variations(self, celebrity_key):
        """Generate name variations for better matching"""
        variations = [celebrity_key.replace('_', ' ')]

        # Add common name mappings
        name_mappings = {
            'trump': ['donald trump', 'trump', 'president trump'],
            'taylor_swift': ['taylor swift', 'swift', 't-swift'],
            'kanye': ['kanye west', 'kanye', 'ye', 'yeezy'],
            'kardashian': ['kim kardashian', 'kardashian', 'kim k'],
            'elon_musk': ['elon musk', 'musk', 'elon'],
            'diddy': ['sean combs', 'p diddy', 'puff daddy', 'diddy'],
            'bieber': ['justin bieber', 'bieber'],
            'drake': ['drake', 'aubrey graham'],
            'beyonce': ['beyoncé', 'beyonce', 'queen b'],
            # Add more mappings as needed
        }

        if celebrity_key in name_mappings:
            variations.extend(name_mappings[celebrity_key])

        return variations

    def detect_potential_celebrities(self, title, content):
        """Auto-discovery of potential new celebrities"""
        text = f"{title} {content}"

        # Look for patterns that suggest celebrity names
        # Capitalized names, often with titles or context clues
        patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b(?=.*(?:actor|actress|singer|rapper|celebrity|star|musician|artist))',
            r'\b(?:actor|actress|singer|rapper|celebrity|star|musician|artist)\s+([A-Z][a-z]+ [A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:performs|releases|announces|arrested|married|divorced)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if len(name) > 5 and name not in [v for variations in [self.get_name_variations(k) for k in self.celebrities.keys()] for v in variations]:
                    self.potential_new_celebrities[name] += 1

    def is_memorial_expired(self, celebrity_data):
        """Check if memorial period has expired"""
        if 'memorial_expires' not in celebrity_data:
            return False

        try:
            expire_date = datetime.strptime(celebrity_data['memorial_expires'], '%Y-%m-%d')
            return datetime.now() > expire_date
        except:
            return False

    def scrape_feed(self, feed_name, feed_info):
        """Scrape individual RSS feed with enhanced processing"""
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

            for entry in feed.entries[:20]:  # Limit to recent articles
                # Check if article is recent (last 24 hours)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(days=1):
                        continue

                title = self.clean_text(entry.get('title', ''))
                content = self.clean_text(entry.get('summary', '') or entry.get('description', ''))
                link = entry.get('link', '')

                if not title:
                    continue

                # Extract celebrity mentions
                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])

                # Auto-discovery
                self.detect_potential_celebrities(title, content)

                if mentions:
                    # Create blog post
                    post_data = self.create_blog_post(title, content, link, mentions, feed_name)
                    if post_data:
                        self.new_posts.append(post_data)
                        articles_processed += 1

            logger.info(f"Processed {articles_processed} articles from {feed_name}")
            time.sleep(1)  # Be nice to servers

        except Exception as e:
            logger.error(f"Error scraping {feed_name}: {e}")

    def create_blog_post(self, title, content, link, mentions, source):
        """Create Jekyll blog post with enhanced metadata"""
        # Generate filename
        date_str = datetime.now().strftime('%Y-%m-%d')
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
        slug = re.sub(r'\s+', '-', slug).lower()[:50]
        filename = f"{date_str}-{slug}.md"

        # Determine primary celebrity and drama level
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

        # Create post content
        post_content = f"""---
layout: post
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} +0000
categories: gossip
tags: {tags}
drama_score: {total_drama_score}
primary_celebrity: {primary_celebrity}
source: {source}
source_url: "{link}"
mentions: {dict(mentions)}
---

{content[:500]}{'...' if len(content) > 500 else ''}

**Drama Score:** {total_drama_score} | **Level:** {drama_level.upper()}

**Celebrities Mentioned:** {', '.join([k.replace('_', ' ').title() for k in mentions.keys()])}

[Read full article at {source.replace('_', ' ').title()}]({link})

---
*This post was automatically generated from RSS feeds. Drama scores are calculated based on mention frequency and source reliability.*
"""

        return {
            'filename': filename,
            'content': post_content,
            'drama_score': total_drama_score,
            'mentions': mentions
        }

    def update_celebrity_scores(self):
        """Update celebrity drama scores based on recent mentions"""
        for celebrity_key, mentions in self.celebrity_mentions.items():
            if celebrity_key in self.celebrities:
                current_score = self.celebrities[celebrity_key].get('drama_score', 0)
                # Decay old score slightly and add new mentions
                new_score = int(current_score * 0.95 + mentions)
                self.celebrities[celebrity_key]['drama_score'] = new_score

                # Update status based on score
                if new_score >= 1500:
                    self.celebrities[celebrity_key]['status'] = 'explosive'
                elif new_score >= 800:
                    self.celebrities[celebrity_key]['status'] = 'hot'
                elif new_score >= 300:
                    self.celebrities[celebrity_key]['status'] = 'rising'
                else:
                    self.celebrities[celebrity_key]['status'] = 'cooling'

    def check_auto_discovery(self):
        """Check if any potential celebrities should be added"""
        new_celebrities = {}

        for name, count in self.potential_new_celebrities.items():
            # Threshold: 5+ mentions in this scrape cycle
            if count >= 5:
                celebrity_key = name.lower().replace(' ', '_')
                new_celebrities[celebrity_key] = {
                    'drama_score': count * 10,  # Initial score
                    'tags': ['auto-discovered', 'new'],
                    'category': 'unknown',
                    'status': 'rising',
                    'discovered_date': datetime.now().strftime('%Y-%m-%d')
                }
                logger.info(f"Auto-discovered potential celebrity: {name}")

        return new_celebrities

    def save_data(self):
        """Save all updated data"""
        # Save updated celebrities
        with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
            yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)

        # Save drama tracking data
        self.drama_data['last_update'] = datetime.now().isoformat()
        self.drama_data['daily_mentions'] = dict(self.celebrity_mentions)

        with open(self.base_path / '_data' / 'drama_tracking.yml', 'w') as f:
            yaml.dump(self.drama_data, f, default_flow_style=False)

        # Save new posts
        posts_dir = self.base_path / '_posts'
        posts_dir.mkdir(exist_ok=True)

        for post in self.new_posts:
            post_path = posts_dir / post['filename']
            with open(post_path, 'w') as f:
                f.write(post['content'])

        logger.info(f"Created {len(self.new_posts)} new posts")

    def run(self):
        """Main scraping process"""
        logger.info("Starting Enhanced Gossip Room scraper...")

        # Scrape all feeds
        for feed_name, feed_info in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_info)

        # Update celebrity scores
        self.update_celebrity_scores()

        # Check for auto-discoveries
        new_celebrities = self.check_auto_discovery()
        if new_celebrities:
            self.celebrities.update(new_celebrities)
            logger.info(f"Added {len(new_celebrities)} new celebrities via auto-discovery")

        # Save all data
        self.save_data()

        logger.info("Gossip scraping complete!")
        logger.info(f"Total mentions tracked: {sum(self.celebrity_mentions.values())}")
        logger.info(f"New posts created: {len(self.new_posts)}")

if __name__ == "__main__":
    scraper = EnhancedGossipScraper()
    scraper.run()
