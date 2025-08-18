#!/usr/bin/env python3
"""
Complete Adaptive Temperature-Based Gossip Scraper with Dynamic Celebrity Scoring & Auto-Discovery
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
        self.celebrity_article_mentions = defaultdict(set)  # Track unique articles per celebrity
        self.potential_new_celebrities = Counter()
        self.new_celebrities_discovered = []

        # Adaptive temperature settings
        self.DAILY_POST_LIMIT = 33
        self.TARGET_POSTS_PER_RUN = 3
        self.FALLBACK_MIN_TEMP = 15
        self.IDEAL_MIN_TEMP = 35
        self.ARCHIVE_DAYS = 30

        # CELEBRITY SCORING SYSTEM 🎯
        self.SCORING_CONFIG = {
            'base_article_points': 1.0,      # Base points per article mention
            'headline_bonus': 0.5,           # Extra if in headline
            'explosive_keywords_bonus': 2.0, # Bonus for drama keywords
            'daily_decay_rate': 0.003,       # 0.3% daily decay
            'weekly_decay_rate': 0.02,       # 2% weekly decay  
            'monthly_decay_rate': 0.08,      # 8% monthly decay
            'monthly_max_articles': 1000,    # ~33 articles/day × 30 days
            'rank_scale': 100,               # Scale to 0-100 ranking
            'new_celebrity_threshold': 2,    # Mentions needed to add new celebrity
            'starting_drama_score': 25       # Starting score for new celebrities
        }

        # CELEBRITY AUTO-DISCOVERY PATTERNS 🔍
        self.CELEBRITY_PATTERNS = {
            # Family relationships
            'family': [
                r"(\w+(?:\s+\w+)?)'s (?:daughter|son|child|kid)",
                r"(\w+(?:\s+\w+)?)'s (?:wife|husband|partner|boyfriend|girlfriend)",
                r"(\w+(?:\s+\w+)?)'s (?:mother|father|parent|mom|dad)",
                r"(\w+(?:\s+\w+)?)'s (?:sister|brother|sibling)",
                r"(\w+(?:\s+\w+)?)'s (?:ex-wife|ex-husband|ex-partner|ex-boyfriend|ex-girlfriend)"
            ],
            # Professional relationships
            'professional': [
                r"(?:actor|actress|singer|rapper|musician|model|influencer|celebrity)\s+(\w+(?:\s+\w+)?)",
                r"(\w+(?:\s+\w+)?)\s+(?:stars?|performs?|sings?|acts?)",
                r"(?:director|producer|writer)\s+(\w+(?:\s+\w+)?)",
                r"(\w+(?:\s+\w+)?)\s+(?:released|dropped|announced)"
            ],
            # Context clues
            'context': [
                r"(\w+(?:\s+\w+)?)\s+(?:was spotted|seen|photographed|caught)",
                r"(\w+(?:\s+\w+)?)\s+(?:reveals?|admits?|confesses?|says?|tells?)",
                r"(\w+(?:\s+\w+)?)\s+(?:dating|married|engaged|divorced)"
            ]
        }

        # RSS feeds - 12 optimized sources
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
            'vogue': {'url': 'https://www.vogue.com/feed/rss', 'weight': 1}
        }

    def load_celebrities(self):
        """Load celebrity database with enhanced name handling"""
        try:
            celebrities_file = self.base_path / '_data' / 'celebrities.yml'
            if celebrities_file.exists():
                with open(celebrities_file, 'r', encoding='utf-8') as f:
                    celebrities = yaml.safe_load(f) or {}

                # FIX PROBLEMATIC NAMES 🔧
                celebrities = self.fix_celebrity_names(celebrities)
                return celebrities
            else:
                logger.info("No celebrities.yml found, starting with empty database")
                return {}
        except Exception as e:
            logger.error(f"Error loading celebrities: {e}")
            return {}

    def fix_celebrity_names(self, celebrities):
        """Fix problematic celebrity name configurations"""
        fixes_applied = []

        # FIX: "ye" -> Only match as "Kanye" or "Kanye West"
        if 'ye' in celebrities:
            ye_data = celebrities.pop('ye')
            celebrities['kanye_west'] = {
                **ye_data,
                'name': 'Kanye West',
                'aliases': ['kanye', 'kanye west'],
                'disambiguation': 'rapper formerly known as Kanye',
                'search_terms': ['kanye west', 'kanye'],  # Never search for just "ye"
            }
            fixes_applied.append("ye -> kanye_west")

        # FIX: "liam" -> "liam_payne" with disambiguation
        if 'liam' in celebrities:
            liam_data = celebrities.pop('liam')
            # Check if this is likely Liam Payne based on category
            if liam_data.get('category') in ['actor', 'musician', 'unknown']:
                celebrities['liam_payne'] = {
                    **liam_data,
                    'name': 'Liam Payne',
                    'aliases': ['liam payne'],
                    'disambiguation': 'former One Direction member',
                    'search_terms': ['liam payne'],  # Never search for just "liam"
                    'category': 'musician'
                }
                fixes_applied.append("liam -> liam_payne")

        # 🔧 FIX: "met" -> "met_gala" with specific search terms
        if 'met' in celebrities:
            met_data = celebrities.pop('met')
            celebrities['met_gala'] = {
                **met_data,
                'name': 'Met Gala',
                'aliases': ['met gala', 'metropolitan museum gala'],
                'disambiguation': 'annual fashion fundraising gala',
                'search_terms': ['met gala', 'metropolitan museum gala'],  # Never search for just "met"
                'category': 'event'
            }
            fixes_applied.append("met -> met_gala")

        # ADD: Prince William disambiguation
        if 'prince_william' not in celebrities:
            # Check if there's a generic "william" entry
            william_data = celebrities.pop('william', {})
            celebrities['prince_william'] = {
                **william_data,
                'name': 'Prince William',
                'aliases': ['prince william', 'william prince of wales'],
                'disambiguation': 'husband of Kate Middleton',
                'search_terms': ['prince william', 'william prince'],
                'category': 'royal',
                'drama_score': william_data.get('drama_score', 50),
                'discovery_date': william_data.get('discovery_date', datetime.now().strftime('%Y-%m-%d')),
                'last_temperature_update': william_data.get('last_temperature_update', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'status': william_data.get('status', 'mild'),
                'temperature_change': william_data.get('temperature_change', 0),
                'memorial': False,
                'promotion_date': william_data.get('promotion_date', datetime.now().strftime('%Y-%m-%d'))
            }
            if william_data:
                fixes_applied.append("william -> prince_william")

        if fixes_applied:
            logger.info(f"🔧 Applied celebrity name fixes: {', '.join(fixes_applied)}")

        return celebrities

    def extract_celebrity_names(self):
        """Extract searchable celebrity names with smart disambiguation"""
        search_terms = []

        for celeb_key, celeb_data in self.celebrities.items():
            if isinstance(celeb_data, dict):
                # Use custom search terms if available
                if 'search_terms' in celeb_data:
                    search_terms.extend([term.lower() for term in celeb_data['search_terms']])
                else:
                    # Use name and aliases
                    name = celeb_data.get('name', celeb_key)
                    search_terms.append(name.lower())

                    # Add aliases
                    aliases = celeb_data.get('aliases', [])
                    search_terms.extend([alias.lower() for alias in aliases])

                    # Add name variations for longer names only
                    if ' ' in name and len(name.split()) >= 2:
                        name_parts = name.split()
                        if len(name_parts[0]) > 3 and len(name_parts[-1]) > 3:  # Avoid short names
                            search_terms.append(f"{name_parts[0].lower()} {name_parts[-1].lower()}")

        return list(set(search_terms))

    def discover_new_celebrities(self, title, description):
        """Auto-discover new celebrities using pattern matching with STRICT filtering"""
        full_text = f"{title} {description}"
        discovered = []

        # 🚫 NUCLEAR BLACKLIST - Never consider these as celebrities
        CELEBRITY_BLACKLIST = {
            # Sentence starters/fragments
            'you_are', 'if_you', 'women_to', 'and_encourages', 'to_make', 'still_work',
            'make_an', 'you_still', 'work_from', 'from_home', 'home_and', 'encourages_people',

            # Common phrases that get capitalized
            'new_york', 'los_angeles', 'las_vegas', 'united_states', 'north_america',
            'social_media', 'real_estate', 'high_school', 'middle_east', 'south_korea',
            'prime_minister', 'white_house', 'red_carpet', 'golden_globes', 'harassing_young_actress',

            # Generic terms
            'breaking_news', 'exclusive_interview', 'latest_update', 'hot_gossip',
            'celebrity_news', 'entertainment_tonight', 'people_magazine', 'black_swan',

            # Common non-celebrity capitalized phrases
            'according_to', 'sources_say', 'insider_reveals', 'close_friend',
            'family_member', 'representative_said', 'publicist_confirmed',

            # Sentence fragments that appear in headlines
            'claims_that', 'reveals_shocking', 'admits_to', 'denies_rumors',
            'confirms_relationship', 'announces_divorce', 'spotted_with'
        }

        # ✅ CELEBRITY INDICATORS - Must have at least one of these contexts
        CELEBRITY_CONTEXT_REQUIRED = [
            # Professional titles
            'actor', 'actress', 'singer', 'rapper', 'musician', 'model', 'influencer',
            'director', 'producer', 'writer', 'comedian', 'host', 'presenter',

            # Celebrity actions
            'stars in', 'performs', 'released album', 'dropped single', 'announced tour',
            'walked red carpet', 'attended premiere', 'won award', 'nominated for',

            # Celebrity relationships
            'dating', 'married to', 'engaged to', 'divorced from', 'split from',
            'relationship with', 'spotted with', 'seen kissing', 'holding hands',

            # Celebrity lifestyle
            'instagram post', 'twitter account', 'social media', 'paparazzi photos',
            'red carpet', 'hollywood', 'celebrity', 'famous', 'star'
        ]

        # Look for capitalized names with STRICT validation
        name_pattern = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b'
        potential_names = re.findall(name_pattern, full_text)

        for name in potential_names:
            name_clean = name.strip()
            name_lower = name_clean.lower()
            name_key = re.sub(r'[^\w\s]', '', name_lower).replace(' ', '_')

            # 🚫 IMMEDIATE BLACKLIST CHECK
            if name_key in CELEBRITY_BLACKLIST:
                continue

            # Skip if already known
            if any(name_lower in search_term for search_term in self.celebrity_names):
                continue

            # 🔍 STRICT CONTEXT VALIDATION
            context_found = False
            category = 'unknown'

            # Must have celebrity context in the same article
            full_text_lower = full_text.lower()
            for context_phrase in CELEBRITY_CONTEXT_REQUIRED:
                if context_phrase in full_text_lower:
                    context_found = True

                    # Determine category from context
                    if any(word in context_phrase for word in ['actor', 'actress', 'stars']):
                        category = 'actor'
                    elif any(word in context_phrase for word in ['singer', 'rapper', 'musician', 'album', 'tour']):
                        category = 'musician'
                    elif 'model' in context_phrase:
                        category = 'model'
                    elif 'influencer' in context_phrase:
                        category = 'influencer'
                    break

            # 🚫 REJECT if no celebrity context found
            if not context_found:
                continue

            # 🚫 ADDITIONAL FILTERS

            # Reject common sentence patterns
            sentence_patterns = [
                r'^(you|if|and|the|to|from|with|about|when|where|what|how|why)\s',
                r'\s(are|is|was|were|will|can|should|would|could|might)\s',
                r'\s(to|from|with|about|after|before|during|while|since|until)$',
                r'(work|make|still|encourages|claims|says|tells|reveals)$'
            ]

            skip_name = False
            for pattern in sentence_patterns:
                if re.search(pattern, name_lower):
                    skip_name = True
                    break

            if skip_name:
                continue

            # Reject if name contains common non-name words
            non_name_words = [
                'you', 'are', 'if', 'still', 'work', 'make', 'and', 'encourages',
                'claims', 'says', 'tells', 'reveals', 'according', 'sources',
                'breaking', 'exclusive', 'latest', 'update', 'news', 'report'
            ]

            if any(word in name_lower.split() for word in non_name_words):
                continue

            # Reject very long names (likely sentences)
            if len(name_clean.split()) > 3:
                continue

            # 🎯 PROXIMITY CHECK - Celebrity context must be near the name
            name_position = full_text_lower.find(name_lower)
            if name_position != -1:
                # Check 100 characters before and after the name
                context_window = full_text_lower[max(0, name_position-100):name_position+len(name_lower)+100]

                context_nearby = any(phrase in context_window for phrase in CELEBRITY_CONTEXT_REQUIRED)
                if not context_nearby:
                    continue

            # ✅ PASSED ALL FILTERS - This might be a real celebrity
            self.potential_new_celebrities[name_clean] += 1
            discovered.append({
                'name': name_clean,
                'category': category,
                'context_score': 3.0,  # High confidence due to strict filtering
                'source_text': full_text[:200] + '...'
            })

        return discovered

    def add_new_celebrity(self, name, category='unknown', context_score=0):
        """Add a new celebrity to the database"""
        # Create celebrity key (lowercase, underscores)
        celeb_key = re.sub(r'[^\w\s]', '', name.lower()).replace(' ', '_')

        # Avoid duplicates
        if celeb_key in self.celebrities:
            return False

        now = datetime.now()

        # Create new celebrity entry
        self.celebrities[celeb_key] = {
            'name': name,
            'category': category,
            'drama_score': self.SCORING_CONFIG['starting_drama_score'],
            'discovery_date': now.strftime('%Y-%m-%d'),
            'last_temperature_update': now.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'mild',
            'temperature_change': 0,
            'memorial': False,
            'promotion_date': now.strftime('%Y-%m-%d'),
            'monthly_rank': 0,
            'context_score': context_score,
            'auto_discovered': True
        }

        # Add to search terms
        self.celebrity_names.append(name.lower())
        if ' ' in name:
            name_parts = name.split()
            if len(name_parts) >= 2 and len(name_parts[0]) > 3 and len(name_parts[-1]) > 3:
                self.celebrity_names.append(f"{name_parts[0].lower()} {name_parts[-1].lower()}")

        self.new_celebrities_discovered.append(name)
        logger.info(f"🌟 NEW CELEBRITY DISCOVERED: {name} ({category}) - Starting at {self.SCORING_CONFIG['starting_drama_score']}°")

        return True

    def process_potential_new_celebrities(self):
        """Process potential new celebrities and add qualifying ones"""
        threshold = self.SCORING_CONFIG['new_celebrity_threshold']

        for name, mention_count in self.potential_new_celebrities.items():
            if mention_count >= threshold:
                # Try to determine category from recent context
                category = 'unknown'

                # Simple category detection based on name patterns or context
                if any(word in name.lower() for word in ['prince', 'princess', 'duke', 'duchess']):
                    category = 'royal'
                elif name.endswith(' Jr.') or name.endswith(' Sr.'):
                    category = 'family'  # Likely family member

                self.add_new_celebrity(name, category, mention_count)

    def contains_celebrity(self, text, title=""):
        """Enhanced celebrity detection with disambiguation"""
        text_lower = text.lower()
        title_lower = title.lower()
        mentioned_celebrities = {}

        for celeb_key, celeb_data in self.celebrities.items():
            if isinstance(celeb_data, dict):
                # Use search terms if available
                search_terms = celeb_data.get('search_terms', [])
                if not search_terms:
                    # Fallback to name and aliases
                    name = celeb_data.get('name', celeb_key)
                    search_terms = [name] + celeb_data.get('aliases', [])

                for term in search_terms:
                    term_lower = term.lower()

                    # Count mentions in text
                    text_count = text_lower.count(term_lower)
                    title_count = title_lower.count(term_lower)

                    if text_count > 0 or title_count > 0:
                        # Apply context filtering for ambiguous names
                        if self.is_valid_celebrity_mention(term_lower, text_lower, celeb_data):
                            mentioned_celebrities[celeb_key] = {
                                'text_mentions': text_count,
                                'title_mentions': title_count,
                                'total_mentions': text_count + title_count,
                                'in_headline': title_count > 0
                            }
                            break  # Found this celebrity, move to next

        return mentioned_celebrities

    def is_valid_celebrity_mention(self, term, text, celeb_data):
        """Context-based validation for celebrity mentions"""
        # Skip very short terms that are likely false positives
        if len(term) <= 2:
            return False

        # Category-based context validation
        category = celeb_data.get('category', '').lower()

        # For musicians, look for music context
        if category == 'musician':
            music_context = any(word in text for word in [
                'album', 'song', 'music', 'concert', 'tour', 'rapper', 'singer', 
                'band', 'performance', 'lyrics', 'record', 'studio'
            ])
            if term in ['liam', 'william'] and not music_context:
                return False

        # For royals, look for royal context
        elif category == 'royal':
            royal_context = any(word in text for word in [
                'prince', 'princess', 'royal', 'palace', 'crown', 'king', 'queen',
                'duchess', 'duke', 'windsor', 'cambridge', 'wales'
            ])
            if term in ['william'] and not royal_context:
                return False

        return True

    def apply_celebrity_scoring_boost(self, article_id, mentions, title, description):
        """Apply scoring boosts to celebrities mentioned in this article"""
        now = datetime.now()

        for celeb_key, mention_data in mentions.items():
            if celeb_key not in self.celebrities:
                continue

            # Track unique articles (not mention count per article)
            self.celebrity_article_mentions[celeb_key].add(article_id)

            # Calculate boost for this article
            boost = self.SCORING_CONFIG['base_article_points']

            # Headline bonus
            if mention_data.get('in_headline', False):
                boost += self.SCORING_CONFIG['headline_bonus']

            # Explosive keywords bonus
            full_text = f"{title} {description}".lower()
            explosive_keywords = [
                'scandal', 'affair', 'cheating', 'divorce', 'breakup', 'fight', 
                'feud', 'drama', 'controversy', 'arrest', 'lawsuit', 'explosive',
                'bombshell', 'shocking', 'secret', 'reveals'
            ]

            if any(keyword in full_text for keyword in explosive_keywords):
                boost += self.SCORING_CONFIG['explosive_keywords_bonus']

            # Apply boost to celebrity
            current_score = self.celebrities[celeb_key].get('drama_score', 50)
            new_score = min(100, current_score + boost)

            # Calculate temperature change
            temp_change = new_score - current_score

            self.celebrities[celeb_key]['drama_score'] = round(new_score, 1)
            self.celebrities[celeb_key]['last_temperature_update'] = now.strftime('%Y-%m-%d %H:%M:%S')
            self.celebrities[celeb_key]['temperature_change'] = round(temp_change, 1)

            # Update status based on score
            self.celebrities[celeb_key]['status'] = self.calculate_celebrity_status(new_score)

            logger.info(f"🎯 {celeb_key}: {current_score:.1f} -> {new_score:.1f} (+{boost:.1f})")

    def apply_celebrity_decay(self):
        """Apply time-based decay to all celebrities"""
        now = datetime.now()

        for celeb_key, celeb_data in self.celebrities.items():
            if not isinstance(celeb_data, dict):
                continue

            last_update_str = celeb_data.get('last_temperature_update')
            if not last_update_str:
                continue

            try:
                last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
                hours_since_update = (now - last_update).total_seconds() / 3600

                # Calculate decay
                decay = 0
                if hours_since_update >= 24 * 30:  # 30+ days
                    decay = self.SCORING_CONFIG['monthly_decay_rate']
                elif hours_since_update >= 24 * 7:  # 7+ days
                    decay = self.SCORING_CONFIG['weekly_decay_rate']
                elif hours_since_update >= 24:  # 1+ day
                    decay = self.SCORING_CONFIG['daily_decay_rate']

                if decay > 0:
                    current_score = celeb_data.get('drama_score', 50)
                    decay_amount = current_score * decay
                    new_score = max(0, current_score - decay_amount)

                    # Calculate temperature change (negative for decay)
                    temp_change = -(decay_amount)

                    self.celebrities[celeb_key]['drama_score'] = round(new_score, 1)
                    self.celebrities[celeb_key]['status'] = self.calculate_celebrity_status(new_score)
                    self.celebrities[celeb_key]['temperature_change'] = round(temp_change, 1)

                    if decay_amount > 0.1:  # Only log significant decay
                        logger.info(f"⏰ {celeb_key}: {current_score:.1f} -> {new_score:.1f} (-{decay_amount:.1f} decay)")

            except ValueError:
                continue

    def calculate_celebrity_status(self, drama_score):
        """Calculate celebrity status based on drama score"""
        if drama_score >= 80:
            return 'explosive'
        elif drama_score >= 60:
            return 'hot'
        elif drama_score >= 40:
            return 'warm'
        elif drama_score >= 20:
            return 'mild'
        else:
            return 'cooling'

    def calculate_celebrity_monthly_rank(self, celeb_key):
        """Calculate celebrity's rank out of 100 based on monthly activity"""
        # Get articles mentioning this celebrity in the last 30 days
        monthly_articles = len(self.celebrity_article_mentions.get(celeb_key, set()))

        # Calculate rank (0-100 scale)
        rank = min(100, (monthly_articles / self.SCORING_CONFIG['monthly_max_articles']) * 100)

        return round(rank, 1)

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

    def extract_celebrity_mentions(self, title, description):
        """Extract celebrity mentions from title and description"""
        mentions = self.contains_celebrity(f"{title} {description}", title)

        # Update global celebrity mention counter
        for celeb_key, mention_data in mentions.items():
            self.celebrity_mentions[celeb_key] += mention_data['total_mentions']

        return mentions

    def calculate_drama_score(self, title, description, mentions):
        """Calculate drama score based on content and celebrity temperatures"""
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

        # Celebrity boost based on their current drama scores
        celebrity_boost = 0
        if mentions:
            for celeb_key, mention_data in mentions.items():
                celeb_data = self.celebrities.get(celeb_key, {})
                celeb_drama_score = celeb_data.get('drama_score', 50)
                celebrity_boost += celeb_drama_score * mention_data['total_mentions']

            celebrity_boost = celebrity_boost / len(mentions)

        # Combine scores - now articles inherit celebrity temperatures!
        total_score = score + (celebrity_boost * 0.6)

        return min(100, max(0, int(total_score)))

    def calculate_temperature(self, drama_score, mentions, pub_date):
        """Calculate temperature using celebrity-driven scoring"""
        base_temp = drama_score

        # Celebrity temperature boost (now more accurate)
        celebrity_boost = 0
        if mentions:
            for celeb_key, mention_data in mentions.items():
                celeb_data = self.celebrities.get(celeb_key, {})
                celeb_temp = celeb_data.get('drama_score', 50)
                celebrity_boost += celeb_temp * mention_data['total_mentions']
            celebrity_boost = celebrity_boost / len(mentions) if mentions else 0

        # Time decay
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
            primary_celeb_key = max(mentions.items(), key=lambda x: x[1]['total_mentions'])[0]
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
            'mentions': {k: v['total_mentions'] for k, v in mentions.items()},
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
        """Scrape individual RSS feed with celebrity scoring and auto-discovery"""
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

            for entry in feed.entries[:10]:
                # Create unique ID for deduplication
                article_id = hashlib.md5(f"{entry.get('link', '')}{entry.get('title', '')}".encode()).hexdigest()

                if article_id in self.processed_articles:
                    continue

                title = entry.get('title', '')
                description = entry.get('summary', entry.get('description', ''))

                # 🔍 AUTO-DISCOVER NEW CELEBRITIES
                discovered = self.discover_new_celebrities(title, description)

                # Extract celebrity mentions (including newly discovered ones)
                mentions = self.extract_celebrity_mentions(title, description)

                # Skip if no celebrity mentions
                if not mentions:
                    continue

                # 🎯 APPLY CELEBRITY SCORING BOOSTS
                self.apply_celebrity_scoring_boost(article_id, mentions, title, description)

                # Calculate scores (now celebrity-driven)
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

    def save_celebrities_yml(self):
        """Save celebrities.yml with proper formatting"""
        try:
            celebrities_dir = self.base_path / '_data'
            celebrities_dir.mkdir(exist_ok=True)

            # Create backup
            celebrities_file = celebrities_dir / 'celebrities.yml'
            if celebrities_file.exists():
                backup_file = celebrities_dir / f'celebrities_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.yml'
                shutil.copy2(celebrities_file, backup_file)
                logger.info(f"📋 Created backup: {backup_file.name}")

            # Save updated celebrities
            with open(celebrities_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True, allow_unicode=True)

            logger.info(f"💾 Saved {len(self.celebrities)} celebrities to celebrities.yml")

        except Exception as e:
            logger.error(f"❌ Error saving celebrities.yml: {e}")

    def save_data(self):
        """Save all data including updated celebrities"""
        Path('data').mkdir(exist_ok=True)

        logger.info(f"🌡️ Found {len(self.new_posts)} potential posts")

        # Process potential new celebrities before publishing
        self.process_potential_new_celebrities()

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

        # 💾 SAVE UPDATED CELEBRITIES.YML
        self.save_celebrities_yml()

    def run(self):
        """Main execution with celebrity scoring and auto-discovery"""
        logger.info("🎭 Starting Adaptive Gossip Scraper with Celebrity Scoring & Auto-Discovery...")

        # 1. Apply decay to all celebrities first
        logger.info("⏰ Applying celebrity score decay...")
        self.apply_celebrity_decay()

        # 2. Scrape all feeds (this will boost celebrity scores and discover new ones)
        for feed_name, feed_config in self.rss_feeds.items():
            self.scrape_feed(feed_name, feed_config)
            time.sleep(2)

        # 3. Calculate monthly ranks for all celebrities
        logger.info("📊 Calculating celebrity monthly ranks...")
        for celeb_key in self.celebrities:
            monthly_rank = self.calculate_celebrity_monthly_rank(celeb_key)
            self.celebrities[celeb_key]['monthly_rank'] = monthly_rank

        # 4. Save data (including updated celebrities.yml)
        self.save_data()

        # 5. Log results
        if self.new_celebrities_discovered:
            logger.info(f"🌟 NEW CELEBRITIES DISCOVERED: {', '.join(self.new_celebrities_discovered)}")

        top_celebs = sorted(
            [(k, v.get('drama_score', 0)) for k, v in self.celebrities.items() if isinstance(v, dict)],
            key=lambda x: x[1], reverse=True
        )[:10]

        logger.info("🏆 Top 10 Hottest Celebrities:")
        for i, (celeb, score) in enumerate(top_celebs, 1):
            status = self.celebrities[celeb].get('status', 'unknown')
            logger.info(f"  {i}. {celeb}: {score:.1f}° ({status})")

        logger.info("✅ Scraping complete!")

if __name__ == "__main__":
    scraper = AdaptiveGossipScraper()
    scraper.run()
