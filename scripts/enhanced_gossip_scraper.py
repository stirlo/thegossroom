#!/usr/bin/env python3
"""
Adaptive Temperature-Based Gossip Scraper
Dynamically adjusts temperature thresholds based on available content
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
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveGossipScraper:
    def __init__(self):
        self.base_path = Path('.')
        self.celebrities = self.load_celebrities()
        self.celebrity_names = self.extract_celebrity_names()
        self.processed_articles = self.load_processed_articles()
        self.daily_queue = self.load_daily_queue()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

        # 🎯 ADAPTIVE TEMPERATURE SETTINGS
        self.DAILY_POST_LIMIT = 33
        self.TARGET_POSTS_PER_RUN = 3  # Aim for 3 posts every 8 hours (24/8 = 3)
        self.FALLBACK_MIN_TEMP = 15    # Emergency fallback if no hot content
        self.IDEAL_MIN_TEMP = 35       # Preferred minimum
        self.ARCHIVE_DAYS = 30

        # RSS feeds (same as before)
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

    def calculate_adaptive_temperature_threshold(self):
        """🎯 ADAPTIVE: Calculate minimum temperature based on available content"""

        # Check how many posts we've published today
        posts_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_today

        logger.info(f"📊 Daily status: {posts_today}/{self.DAILY_POST_LIMIT} posts published")

        if remaining_slots <= 0:
            return 100  # No more posts today

        # If we have very few posts left for the day, be more selective
        if remaining_slots <= 5:
            min_temp = self.IDEAL_MIN_TEMP + 10  # Be pickier
        elif remaining_slots <= 15:
            min_temp = self.IDEAL_MIN_TEMP
        else:
            min_temp = self.IDEAL_MIN_TEMP - 10  # Be more lenient

        # Check recent temperature trends
        recent_temps = self.get_recent_post_temperatures()

        if recent_temps:
            avg_recent_temp = statistics.mean(recent_temps)
            median_recent_temp = statistics.median(recent_temps)

            logger.info(f"🌡️ Recent temperature trends - Avg: {avg_recent_temp:.1f}°, Median: {median_recent_temp:.1f}°")

            # If recent posts are generally cool, lower the threshold
            if avg_recent_temp < 30:
                min_temp = max(self.FALLBACK_MIN_TEMP, min_temp - 15)
                logger.info("❄️ Recent posts are cool - lowering temperature threshold")
            elif avg_recent_temp > 60:
                min_temp = min_temp + 10
                logger.info("🔥 Recent posts are hot - raising temperature threshold")

        # Ensure we don't go below fallback minimum
        final_temp = max(self.FALLBACK_MIN_TEMP, min_temp)

        logger.info(f"🎯 Adaptive temperature threshold: {final_temp}° (remaining slots: {remaining_slots})")
        return final_temp

    def get_recent_post_temperatures(self):
        """Get temperatures of posts from last 3 days"""
        posts_dir = self.base_path / '_posts'
        recent_temps = []

        cutoff_date = datetime.now() - timedelta(days=3)

        for post_file in posts_dir.glob('*.md'):
            try:
                # Extract date from filename
                if post_file.name.startswith('20'):
                    file_date = datetime.strptime(post_file.name[:10], '%Y-%m-%d')
                    if file_date >= cutoff_date:
                        # Read temperature from post
                        with open(post_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        if content.startswith('---'):
                            parts = content.split('---', 2)
                            if len(parts) >= 2:
                                front_matter = yaml.safe_load(parts[1])
                                temp = front_matter.get('temperature', 0)
                                if temp > 0:
                                    recent_temps.append(temp)
            except:
                continue

        return recent_temps

    def ensure_minimum_daily_content(self, filtered_posts, min_temp_used):
        """🎯 EMERGENCY: Ensure we have some content even if it's cooler"""

        posts_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_today

        # If we have very few posts and lots of remaining slots, lower standards
        if len(filtered_posts) < self.TARGET_POSTS_PER_RUN and remaining_slots > 20:
            logger.info(f"⚠️ Only {len(filtered_posts)} posts above {min_temp_used}° - lowering standards")

            # Try with emergency fallback temperature
            emergency_posts = [p for p in self.new_posts if p['temperature'] >= self.FALLBACK_MIN_TEMP]

            if len(emergency_posts) > len(filtered_posts):
                logger.info(f"🆘 Emergency mode: Using {len(emergency_posts)} posts above {self.FALLBACK_MIN_TEMP}°")
                return emergency_posts[:self.TARGET_POSTS_PER_RUN * 2]  # Take a few extra

        return filtered_posts

    def load_daily_queue(self):
        """Load daily posting queue"""
        Path('data').mkdir(exist_ok=True)
        try:
            with open('data/daily_queue.json', 'r') as f:
                queue_data = json.load(f)

                today = datetime.now().strftime('%Y-%m-%d')
                if queue_data.get('date') != today:
                    return {'date': today, 'posted_count': 0, 'queue': []}

                return queue_data
        except FileNotFoundError:
            return {'date': datetime.now().strftime('%Y-%m-%d'), 'posted_count': 0, 'queue': []}

    def get_daily_posts_published_today(self):
        """Count posts already published today"""
        posts_dir = self.base_path / '_posts'
        today = datetime.now().strftime('%Y-%m-%d')

        count = 0
        for post_file in posts_dir.glob(f'{today}-*.md'):
            count += 1

        return count

    # [Include all the other methods from previous version: load_celebrities, extract_celebrity_names, 
    #  clean_text, contains_celebrity, extract_celebrity_mentions, create_clean_slug, 
    #  create_blog_post, scrape_feed, update_celebrity_scores, etc.]

    def manage_daily_posts(self):
        """🎯 ADAPTIVE: Manage daily post limit with dynamic temperature filtering"""
        posts_published_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_published_today

        logger.info(f"📊 Daily Status: {posts_published_today}/{self.DAILY_POST_LIMIT} posts published")

        if remaining_slots <= 0:
            logger.info("🚫 Daily limit reached - queuing posts for tomorrow")
            return []

        # Calculate adaptive temperature threshold
        min_temp = self.calculate_adaptive_temperature_threshold()

        # Filter posts by temperature
        hot_posts = [p for p in self.new_posts if p['temperature'] >= min_temp]

        # Emergency content check
        hot_posts = self.ensure_minimum_daily_content(hot_posts, min_temp)

        # Sort by temperature and take what we need
        hot_posts.sort(key=lambda x: (-x['temperature'], -x.get('drama_score', 0)))

        # Take posts for this run (aim for TARGET_POSTS_PER_RUN)
        posts_to_publish = hot_posts[:min(remaining_slots, self.TARGET_POSTS_PER_RUN)]

        # Queue the rest for later
        queued_posts = hot_posts[len(posts_to_publish):]
        if queued_posts:
            logger.info(f"📋 Queuing {len(queued_posts)} posts for later")
            self.daily_queue['queue'].extend(queued_posts)

        logger.info(f"🎯 Publishing {len(posts_to_publish)} posts this run")
        return posts_to_publish

    def save_data(self):
        """Save data with adaptive temperature filtering"""
        Path('data').mkdir(exist_ok=True)

        logger.info(f"🌡️ Found {len(self.new_posts)} potential posts")

        # Manage daily posting with adaptive thresholds
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

        # Save analytics with adaptive data
        temperature_data = {
            'last_updated': datetime.now().isoformat(),
            'posts_published_today': created_posts,
            'posts_queued': len(self.daily_queue.get('queue', [])),
            'adaptive_threshold_used': self.calculate_adaptive_temperature_threshold(),
            'recent_temperature_avg': statistics.mean(self.get_recent_post_temperatures()) if self.get_recent_post_temperatures() else 0,
            'hottest_celebrities': sorted(self.celebrity_mentions.items(), 
                                        key=lambda x: x[1], reverse=True)[:10],
            'temperature_distribution': {
                'nuclear': len([p for p in self.new_posts if p['temperature'] >= 80]),
                'explosive': len([p for p in self.new_posts if 60 <= p['temperature'] < 80]),
                'hot': len([p for p in self.new_posts if 40 <= p['temperature'] < 60]),
                'warm': len([p for p in self.new_posts if 25 <= p['temperature'] < 40]),
                'cool': len([p for p in self.new_posts if p['temperature'] < 25])
            }
        }

        with open('data/temperature_analytics.json', 'w') as f:
            json.dump(temperature_data, f, indent=2, default=str)

        # Save other data (celebrities, processed articles, etc.)
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

        with open('data/processed_articles.json', 'w') as f:
            json.dump(self.processed_articles, f, indent=2)

        with open('data/daily_queue.json', 'w') as f:
            json.dump(self.daily_queue, f, indent=2, default=str)

    # [Include run() method and other helper methods from previous version]

if __name__ == "__main__":
    scraper = AdaptiveGossipScraper()
    scraper.run()
