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
        self.celebrity_names = self.load_celebrity_names()  # NEW: Load from Celebrities.txt
        self.rss_feeds = self.load_rss_feeds()
        self.drama_data = self.load_drama_data()
        self.new_posts = []
        self.celebrity_mentions = defaultdict(int)
        self.potential_new_celebrities = Counter()

        # NEW: Define gossip and business keywords
        self.gossip_keywords = [
            'drama', 'scandal', 'controversy', 'relationship', 'dating', 
            'breakup', 'marriage', 'divorce', 'affair', 'feud', 'fight',
            'arrest', 'lawsuit', 'court', 'trial', 'charges', 'guilty',
            'pregnant', 'baby', 'wedding', 'engaged', 'split', 'cheating',
            'rehab', 'addiction', 'overdose', 'death', 'died', 'funeral',
            'fashion', 'red carpet', 'awards', 'premiere', 'party',
            'social media', 'instagram', 'twitter', 'tiktok', 'viral',
            'paparazzi', 'photos', 'spotted', 'seen', 'exclusive',
            'romance', 'love', 'hate', 'beef', 'diss', 'shade', 'tea'
        ]

        self.business_keywords = [
            'vc industry', 'venture capital', 'funding round', 'ipo', 
            'stock price', 'earnings', 'quarterly', 'revenue', 'profit',
            'acquisition', 'merger', 'valuation', 'investment', 'startup',
            'cryptocurrency', 'bitcoin', 'blockchain', 'nft', 'defi',
            'software', 'hardware', 'algorithm', 'api', 'database',
            'cloud computing', 'artificial intelligence', 'machine learning',
            'cybersecurity', 'data breach', 'privacy policy', 'market analysis',
            'financial report', 'economic', 'inflation', 'interest rates',
            'gdp', 'unemployment', 'federal reserve', 'wall street'
        ]

    def load_celebrity_names(self):
        """NEW: Load celebrity names from Celebrities.txt"""
        try:
            with open(self.base_path / 'Celebrities.txt', 'r', encoding='utf-8') as f:
                return [line.strip().lower() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            logger.warning("Celebrities.txt not found! Using fallback list.")
            return ['taylor swift', 'kanye west', 'kim kardashian', 'drake', 'beyonce']

    def load_celebrities(self):
        """Load celebrity database"""
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("celebrities.yml not found")
            return {}

    def load_rss_feeds(self):
        """Complete RSS feeds with weights for importance"""
        return {
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
            'high_heel_confidential': {'url': 'http://www.highheelconfidential.com/feed/', 'weight': 1},

            # TIER 3: Sports/Tech/General (Weight 1)
            'espn': {'url': 'https://www.espn.com/espn/rss/news', 'weight': 1},
            'techcrunch': {'url': 'https://techcrunch.com/feed/', 'weight': 1},
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

    def is_celebrity_gossip(self, title, content):
        """NEW: Enhanced filtering - must be celebrity gossip, not business/tech"""
        full_text = f"{title} {content}".lower()

        # Step 1: Must contain at least one celebrity from our list
        celebrity_mentions = []
        for celebrity in self.celebrity_names:
            if celebrity in full_text:
                celebrity_mentions.append(celebrity)

        if not celebrity_mentions:
            logger.debug(f"❌ No celebrity mentions: {title[:50]}...")
            return False, []

        # Step 2: Must have gossip context
        gossip_score = sum(1 for keyword in self.gossip_keywords if keyword in full_text)

        # Step 3: Must NOT be business/tech heavy
        business_score = sum(1 for keyword in self.business_keywords if keyword in full_text)

        # Decision logic
        has_gossip_context = gossip_score >= 1  # At least 1 gossip keyword
        is_business_heavy = business_score >= 2  # 2+ business keywords = reject

        if has_gossip_context and not is_business_heavy:
            logger.info(f"✅ Valid gossip: {len(celebrity_mentions)} celebrities, {gossip_score} gossip keywords")
            return True, celebrity_mentions
        elif not has_gossip_context:
            logger.debug(f"❌ No gossip context: {title[:50]}... (gossip score: {gossip_score})")
            return False, []
        elif is_business_heavy:
            logger.debug(f"❌ Too business-focused: {title[:50]}... (business score: {business_score})")
            return False, []

        return False, []

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
            articles_rejected = 0

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

                # NEW: First check if it's celebrity gossip
                is_gossip, found_celebrities = self.is_celebrity_gossip(title, content)

                if not is_gossip:
                    articles_rejected += 1
                    continue

                # Extract celebrity mentions (existing logic)
                mentions = self.extract_celebrity_mentions(title, content, feed_info['weight'])

                # Auto-discovery
                self.detect_potential_celebrities(title, content)

                if mentions:
                    # Create blog post
                    post_data = self.create_blog_post(title, content, link, mentions, feed_name)
                    if post_data:
                        self.new_posts.append(post_data)
                        articles_processed += 1

            logger.info(f"✅ {feed_name}: {articles_processed} gossip posts, {articles_rejected} rejected")
            time.sleep(1)  # Be nice to servers

        except Exception as e:
            logger.error(f"Error scraping {feed_name}: {e}")

    def create_blog_post(self, title, content, link, mentions, source):
        # Generate filename with proper sanitization
        date_str = datetime.now().strftime('%Y-%m-%d')
    
        # Clean slug generation - prevents trailing hyphens
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
        slug = re.sub(r'\s+', '-', slug).lower()
        slug = slug[:50]  # Truncate first
        slug = slug.strip('-')  # Remove leading/trailing hyphens
    
        # Ensure slug isn't empty after cleaning
        if not slug:
            slug = 'untitled-post'
    
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
        logger.info(f"Loaded {len(self.celebrity_names)} celebrities from Celebrities.txt")

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

        logger.info("🎭 Gossip scraping complete!")
        logger.info(f"Total mentions tracked: {sum(self.celebrity_mentions.values())}")
        logger.info(f"New posts created: {len(self.new_posts)}")

if __name__ == "__main__":
    scraper = EnhancedGossipScraper()
    scraper.run()
