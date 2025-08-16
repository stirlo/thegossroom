#!/usr/bin/env python3
"""
Complete Adaptive Temperature-Based Gossip Scraper
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

        # Adaptive temperature settings
        self.DAILY_POST_LIMIT = 33
        self.TARGET_POSTS_PER_RUN = 3
        self.FALLBACK_MIN_TEMP = 15
        self.IDEAL_MIN_TEMP = 35
        self.ARCHIVE_DAYS = 30

        # RSS feeds
         self.rss_feeds = {
            # PURE GOSSIP GOLD 🔥
            'tmz': {'url': 'https://www.tmz.com/rss.xml', 'weight': 3},
            'page_six': {'url': 'https://pagesix.com/feed/', 'weight': 3},
            'perez_hilton': {'url': 'https://perezhilton.com/feed/', 'weight': 3},
            'us_weekly': {'url': 'https://www.usmagazine.com/feed/', 'weight': 3},
        
            # CELEBRITY NEWS ⭐
            'e_news': {'url': 'http://syndication.eonline.com/syndication/feeds/rssfeeds/topstories.xml', 'weight': 2},
            'daily_mail': {'url': 'https://www.dailymail.co.uk/articles.rss', 'weight': 2},
            'hollywood_reporter': {'url': 'https://www.hollywoodreporter.com/feed/', 'weight': 2},
            'variety': {'url': 'https://variety.com/feed/', 'weight': 2},
        
            # MUSIC/ENTERTAINMENT DRAMA 🎭
            'billboard': {'url': 'https://www.billboard.com/feed/', 'weight': 2},
            'rolling_stone': {'url': 'https://www.rollingstone.com/feed/', 'weight': 2},
        
            # FASHION/LIFESTYLE (Celebrity focused) 💅
            'elle': {'url': 'https://www.elle.com/rss/all.xml/', 'weight': 1},
            'vogue': {'url': 'https://www.vogue.com/feed/rss', 'weight': 1},
    }

    def load_celebrities(self):
        """Load celebrity database"""
        try:
            celebrities_file = self.base_path / '_data' / 'celebrities.yml'
            if celebrities_file.exists():
                with open(celebrities_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.info("No celebrities.yml found, starting with empty database")
                return {}
        except Exception as e:
            logger.error(f"Error loading celebrities: {e}")
            return {}

    def extract_celebrity_names(self):
        """Extract searchable celebrity names"""
        names = []
        for celeb_key, celeb_data in self.celebrities.items():
            if isinstance(celeb_data, dict):
                name = celeb_data.get('name', celeb_key)
                names.append(name.lower())

                # Add variations
                if ' ' in name:
                    names.extend([part.lower() for part in name.split() if len(part) > 2])

        return list(set(names))

    def load_processed_articles(self):
        """Load processed articles to avoid duplicates"""
        try:
            with open('data/processed_articles.json', 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()

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

    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""

        # HTML decode
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def contains_celebrity(self, text):
        """Check if text contains celebrity mentions"""
        text_lower = text.lower()
        mentioned_celebrities = {}

        for celeb_key, celeb_data in self.celebrities.items():
            if isinstance(celeb_data, dict):
                name = celeb_data.get('name', celeb_key).lower()

                # Count mentions
                count = text_lower.count(name)
                if count > 0:
                    mentioned_celebrities[celeb_key] = count

                # Check name parts for longer names
                if ' ' in name and count == 0:
                    name_parts = name.split()
                    if len(name_parts) >= 2:
                        first_last = f"{name_parts[0]} {name_parts[-1]}"
                        count = text_lower.count(first_last)
                        if count > 0:
                            mentioned_celebrities[celeb_key] = count

        return mentioned_celebrities

    def extract_celebrity_mentions(self, title, description):
        """Extract celebrity mentions from title and description"""
        full_text = f"{title} {description}".lower()
        mentions = self.contains_celebrity(full_text)

        # Update global celebrity mention counter
        for celeb_key, count in mentions.items():
            self.celebrity_mentions[celeb_key] += count

        return mentions

    def calculate_drama_score(self, title, description, mentions):
        """Calculate drama score based on content"""
        full_text = f"{title} {description}".lower()

        # Drama keywords with weights
        drama_keywords = {
            'scandal': 15, 'affair': 12, 'cheating': 12, 'divorce': 10,
            'breakup': 8, 'fight': 8, 'feud': 10, 'drama': 8,
            'controversy': 10, 'arrest': 15, 'lawsuit': 12, 'sued': 12,
            'rehab': 10, 'addiction': 10, 'overdose': 15, 'death': 20,
            'pregnant': 8, 'baby': 6, 'wedding': 6, 'engaged': 6,
            'secret': 8, 'reveals': 6, 'confession': 8, 'admits': 6,
            'shocking': 8, 'explosive': 10, 'bombshell': 12, 'exclusive': 6
        }

        score = 0
        for keyword, weight in drama_keywords.items():
            count = full_text.count(keyword)
            score += count * weight

        # Celebrity boost
        celebrity_boost = 0
        if mentions:
            for celeb_key, mention_count in mentions.items():
                celeb_data = self.celebrities.get(celeb_key, {})
                celeb_drama_score = celeb_data.get('drama_score', 50)
                celebrity_boost += celeb_drama_score * mention_count

            celebrity_boost = celebrity_boost / len(mentions)

        # Combine scores
        total_score = score + (celebrity_boost * 0.6)

        return min(100, max(0, int(total_score)))

    def calculate_temperature(self, drama_score, mentions, pub_date):
        """Calculate temperature (hotness) of gossip"""
        base_temp = drama_score

        # Celebrity temperature boost
        celebrity_boost = 0
        if mentions:
            for celeb_key, mention_count in mentions.items():
                celeb_data = self.celebrities.get(celeb_key, {})
                celeb_temp = celeb_data.get('drama_score', 50)
                celebrity_boost += celeb_temp * mention_count
            celebrity_boost = celebrity_boost / len(mentions) if mentions else 0

        # Time decay (gossip gets cooler over time)
        time_penalty = 0
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    pub_datetime = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                else:
                    pub_datetime = pub_date

                hours_old = (datetime.now() - pub_datetime.replace(tzinfo=None)).total_seconds() / 3600

                if hours_old > 48:
                    time_penalty = 15
                elif hours_old > 24:
                    time_penalty = 10
                elif hours_old > 12:
                    time_penalty = 5
            except:
                time_penalty = 5

        temperature = base_temp + (celebrity_boost * 0.4) - time_penalty
        return max(0, min(100, int(temperature)))

    def create_clean_slug(self, title):
        """Create URL-friendly slug"""
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:50].strip('-')

    def create_blog_post(self, article, source_name, drama_score, temperature, mentions):
        """Create Jekyll blog post"""
        title = self.clean_text(article.get('title', 'Untitled'))
        description = self.clean_text(article.get('summary', article.get('description', '')))
        link = article.get('link', '')
        pub_date = article.get('published_parsed')

        if pub_date:
            pub_datetime = datetime(*pub_date[:6])
        else:
            pub_datetime = datetime.now()

        # Create filename
        date_str = pub_datetime.strftime('%Y-%m-%d')
        slug = self.create_clean_slug(title)
        filename = f"{date_str}-{slug}.md"

        # Determine primary celebrity
        primary_celebrity = ""
        if mentions:
            primary_celeb_key = max(mentions.items(), key=lambda x: x[1])[0]
            primary_celebrity = self.celebrities.get(primary_celeb_key, {}).get('name', primary_celeb_key)

        # Create front matter
        front_matter = {
            'layout': 'post',
            'title': title,
            'date': pub_datetime.isoformat(),
            'source': source_name,
            'source_url': link,
            'drama_score': drama_score,
            'temperature': temperature,
            'primary_celebrity': primary_celebrity,
            'mentions': mentions,
            'categories': ['gossip', 'entertainment'],
            'tags': list(mentions.keys()) if mentions else []
        }

        # Create post content
        content = f"""---
{yaml.dump(front_matter, default_flow_style=False, sort_keys=True)}---

{description}

[Read more at {source_name}]({link})
"""

        return {
            'filename': filename,
            'content': content,
            'title': title,
            'temperature': temperature,
            'drama_score': drama_score,
            'mentions': mentions,
            'pub_date': pub_datetime
        }

    def scrape_feed(self, feed_name, feed_config):
        """Scrape individual RSS feed"""
        try:
            logger.info(f"Scraping {feed_name}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(feed_config['url'], headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"No entries found in {feed_name}")
                return

            for entry in feed.entries[:10]:  # Limit to recent entries
                # Create unique ID for deduplication
                article_id = hashlib.md5(f"{entry.get('link', '')}{entry.get('title', '')}".encode()).hexdigest()

                if article_id in self.processed_articles:
                    continue

                # Extract celebrity mentions
                title = entry.get('title', '')
                description = entry.get('summary', entry.get('description', ''))
                mentions = self.extract_celebrity_mentions(title, description)

                # Skip if no celebrity mentions
                if not mentions:
                    continue

                # Calculate scores
                drama_score = self.calculate_drama_score(title, description, mentions)
                pub_date = entry.get('published_parsed')
                temperature = self.calculate_temperature(drama_score, mentions, pub_date)

                # Create blog post
                post = self.create_blog_post(entry, feed_name, drama_score, temperature, mentions)
                self.new_posts.append(post)
                self.processed_articles.add(article_id)

                logger.info(f"Found: {title[:50]}... (🌡️{temperature}°)")

        except Exception as e:
            logger.error(f"Error scraping {feed_name}: {e}")

    def calculate_adaptive_temperature_threshold(self):
        """Calculate minimum temperature based on available content"""
        posts_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_today

        logger.info(f"📊 Daily status: {posts_today}/{self.DAILY_POST_LIMIT} posts published")

        if remaining_slots <= 0:
            return 100

        if remaining_slots <= 5:
            min_temp = self.IDEAL_MIN_TEMP + 10
        elif remaining_slots <= 15:
            min_temp = self.IDEAL_MIN_TEMP
        else:
            min_temp = self.IDEAL_MIN_TEMP - 10

        recent_temps = self.get_recent_post_temperatures()

        if recent_temps:
            avg_recent_temp = statistics.mean(recent_temps)
            if avg_recent_temp < 30:
                min_temp = max(self.FALLBACK_MIN_TEMP, min_temp - 15)
            elif avg_recent_temp > 60:
                min_temp = min_temp + 10

        final_temp = max(self.FALLBACK_MIN_TEMP, min_temp)
        logger.info(f"🎯 Adaptive temperature threshold: {final_temp}°")
        return final_temp

    def get_recent_post_temperatures(self):
        """Get temperatures of posts from last 3 days"""
        posts_dir = self.base_path / '_posts'
        recent_temps = []
        cutoff_date = datetime.now() - timedelta(days=3)

        for post_file in posts_dir.glob('*.md'):
            try:
                if post_file.name.startswith('20'):
                    file_date = datetime.strptime(post_file.name[:10], '%Y-%m-%d')
                    if file_date >= cutoff_date:
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

    def get_daily_posts_published_today(self):
        """Count posts already published today"""
        posts_dir = self.base_path / '_posts'
        today = datetime.now().strftime('%Y-%m-%d')
        return len(list(posts_dir.glob(f'{today}-*.md')))

    def manage_daily_posts(self):
        """Manage daily post limit with adaptive temperature filtering"""
        posts_published_today = self.get_daily_posts_published_today()
        remaining_slots = self.DAILY_POST_LIMIT - posts_published_today

        if remaining_slots <= 0:
            logger.info("🚫 Daily limit reached")
            return []

        min_temp = self.calculate_adaptive_temperature_threshold()
        hot_posts = [p for p in self.new_posts if p['temperature'] >= min_temp]

        # Sort by temperature
        hot_posts.sort(key=lambda x: (-x['temperature'], -x.get('drama_score', 0)))

        posts_to_publish = hot_posts[:min(remaining_slots, self.TARGET_POSTS_PER_RUN)]
        logger.info(f"🎯 Publishing {len(posts_to_publish)} posts this run")
        return posts_to_publish

    def save_data(self):
        """Save all data"""
        Path('data').mkdir(exist_ok=True)

        logger.info(f"🌡️ Found {len(self.new_posts)} potential posts")

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

        # Save processed articles
        with open('data/processed_articles.json', 'w') as f:
            json.dump(list(self.processed_articles), f, indent=2)

        # Save celebrities
        try:
            celebrities_dir = self.base_path / '_data'
            celebrities_dir.mkdir(exist_ok=True)
            with open(celebrities_dir / 'celebrities.yml', 'w') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)
        except Exception as e:
            logger.error(f"Error saving celebrities: {e}")

    def run(self):
        """Main execution"""
        logger.info("🎭 Starting Adaptive Gossip Scraper...")

        # Scrape all feeds
        for feed_name, feed_config in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_config)
            time.sleep(2)  # Be nice to servers

        # Save data
        self.save_data()

        logger.info("✅ Scraping complete!")

if __name__ == "__main__":
    scraper = AdaptiveGossipScraper()
    scraper.run()
