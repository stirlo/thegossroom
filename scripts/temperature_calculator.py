#!/usr/bin/env python3
"""
Celebrity Drama Temperature Calculator
Calculates relative drama scores based on mention frequency, sentiment, and engagement
"""

import yaml
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import math

class TemperatureCalculator:
    def __init__(self):
        self.base_path = Path.cwd()
        self.posts_dir = self.base_path / '_posts'
        self.data_dir = self.base_path / '_data'

        # Load configuration
        self.load_celebrities()
        self.load_tag_management()

        # Temperature thresholds (percentile-based)
        self.temperature_thresholds = {
            'explosive': 90,    # Top 10%
            'hot': 75,          # Top 25%
            'rising': 60,       # Top 40%
            'mild': 40,         # Middle 20%
            'cooling': 25,      # Bottom 35%
            'freezing': 10      # Bottom 10%
        }

        # Scoring weights
        self.weights = {
            'mention_frequency': 0.4,
            'recent_activity': 0.3,
            'engagement_score': 0.2,
            'sentiment_volatility': 0.1
        }

        # Lookback period for calculations
        self.lookback_days = 30

    def load_celebrities(self):
        """Load celebrity database"""
        celebrities_file = self.data_dir / 'celebrities.yml'
        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                self.celebrities = yaml.safe_load(f) or {}
        else:
            self.celebrities = {}

    def load_tag_management(self):
        """Load tag management for celebrity detection"""
        tag_file = self.data_dir / 'tag_management.yml'
        if tag_file.exists():
            with open(tag_file, 'r') as f:
                self.tag_config = yaml.safe_load(f) or {}
        else:
            self.tag_config = {'add_to_whitelist': []}

    def get_recent_posts(self, days=None):
        """Get posts from the last N days"""
        if days is None:
            days = self.lookback_days

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_posts = []

        for post_file in self.posts_dir.glob('*.md'):
            try:
                # Extract date from filename (YYYY-MM-DD format)
                date_str = post_file.stem[:10]
                post_date = datetime.strptime(date_str, '%Y-%m-%d')

                if post_date >= cutoff_date:
                    with open(post_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        recent_posts.append({
                            'file': post_file,
                            'date': post_date,
                            'content': content
                        })
            except (ValueError, IndexError):
                continue

        return recent_posts

    def extract_celebrity_mentions(self, posts):
        """Extract celebrity mentions from posts"""
        celebrity_mentions = defaultdict(list)

        # Get all celebrity names and aliases
        celebrity_names = set()
        for celebrity_id, data in self.celebrities.items():
            # Add the ID as a searchable name
            celebrity_names.add(celebrity_id.replace('_', ' '))
            celebrity_names.add(celebrity_id)

        # Add whitelist names
        if 'add_to_whitelist' in self.tag_config:
            celebrity_names.update(self.tag_config['add_to_whitelist'])

        for post in posts:
            content_lower = post['content'].lower()

            for name in celebrity_names:
                name_lower = name.lower()
                # Count mentions (case-insensitive)
                mention_count = len(re.findall(r'\b' + re.escape(name_lower) + r'\b', content_lower))

                if mention_count > 0:
                    # Find corresponding celebrity ID
                    celebrity_id = self.find_celebrity_id(name)
                    if celebrity_id:
                        celebrity_mentions[celebrity_id].append({
                            'post': post,
                            'mentions': mention_count,
                            'date': post['date']
                        })

        return celebrity_mentions

    def find_celebrity_id(self, name):
        """Find celebrity ID from name"""
        name_lower = name.lower()

        # Direct ID match
        if name_lower.replace(' ', '_') in self.celebrities:
            return name_lower.replace(' ', '_')

        # Search through existing celebrities
        for celebrity_id in self.celebrities:
            if celebrity_id.replace('_', ' ').lower() == name_lower:
                return celebrity_id

        # Create new ID from name
        return name_lower.replace(' ', '_')

    def calculate_mention_frequency(self, mentions):
        """Calculate mention frequency score"""
        if not mentions:
            return 0

        total_mentions = sum(m['mentions'] for m in mentions)
        unique_posts = len(mentions)

        # Frequency score based on total mentions and post spread
        frequency_score = (total_mentions * 10) + (unique_posts * 5)
        return min(frequency_score, 100)

    def calculate_recent_activity(self, mentions):
        """Calculate recent activity score with decay"""
        if not mentions:
            return 0

        now = datetime.now()
        activity_score = 0

        for mention in mentions:
            days_ago = (now - mention['date']).days
            # Exponential decay: more recent = higher score
            decay_factor = math.exp(-days_ago / 7)  # 7-day half-life
            activity_score += mention['mentions'] * decay_factor * 10

        return min(activity_score, 100)

    def calculate_engagement_score(self, mentions):
        """Estimate engagement based on mention patterns"""
        if not mentions:
            return 0

        # Simple heuristic: more posts mentioning = higher engagement
        unique_posts = len(mentions)
        avg_mentions_per_post = sum(m['mentions'] for m in mentions) / unique_posts

        engagement_score = (unique_posts * 8) + (avg_mentions_per_post * 3)
        return min(engagement_score, 100)

    def calculate_sentiment_volatility(self, mentions):
        """Calculate sentiment volatility (placeholder for now)"""
        if not mentions:
            return 0

        # Placeholder: assume higher mention frequency = higher volatility
        total_mentions = sum(m['mentions'] for m in mentions)
        volatility_score = min(total_mentions * 2, 100)

        return volatility_score

    def calculate_temperature(self, celebrity_id, mentions):
        """Calculate overall temperature score"""
        if not mentions:
            return 0

        # Calculate component scores
        mention_freq = self.calculate_mention_frequency(mentions)
        recent_activity = self.calculate_recent_activity(mentions)
        engagement = self.calculate_engagement_score(mentions)
        volatility = self.calculate_sentiment_volatility(mentions)

        # Weighted average
        temperature = (
            mention_freq * self.weights['mention_frequency'] +
            recent_activity * self.weights['recent_activity'] +
            engagement * self.weights['engagement_score'] +
            volatility * self.weights['sentiment_volatility']
        )

        return round(temperature, 1)

    def get_temperature_status(self, temperature, all_temperatures):
        """Get temperature status based on percentile"""
        if not all_temperatures:
            return 'mild'

        percentile = (sum(1 for t in all_temperatures if t < temperature) / len(all_temperatures)) * 100

        if percentile >= self.temperature_thresholds['explosive']:
            return 'explosive'
        elif percentile >= self.temperature_thresholds['hot']:
            return 'hot'
        elif percentile >= self.temperature_thresholds['rising']:
            return 'rising'
        elif percentile >= self.temperature_thresholds['mild']:
            return 'mild'
        elif percentile >= self.temperature_thresholds['cooling']:
            return 'cooling'
        else:
            return 'freezing'

    def calculate_temperature_change(self, celebrity_id, current_temp):
        """Calculate temperature change from previous calculation"""
        if celebrity_id not in self.celebrities:
            return current_temp  # New celebrity

        previous_temp = self.celebrities[celebrity_id].get('drama_score', 0)
        return round(current_temp - previous_temp, 1)

    def update_celebrity_temperatures(self):
        """Main function to update all celebrity temperatures"""
        print("🌡️  Calculating celebrity drama temperatures...")

        # Get recent posts
        recent_posts = self.get_recent_posts()
        print(f"📊 Analyzing {len(recent_posts)} recent posts...")

        # Extract mentions
        celebrity_mentions = self.extract_celebrity_mentions(recent_posts)
        print(f"🎭 Found mentions for {len(celebrity_mentions)} celebrities")

        # Calculate temperatures
        new_temperatures = {}
        for celebrity_id, mentions in celebrity_mentions.items():
            temperature = self.calculate_temperature(celebrity_id, mentions)
            new_temperatures[celebrity_id] = temperature

        # Add existing celebrities with 0 mentions
        for celebrity_id in self.celebrities:
            if celebrity_id not in new_temperatures:
                new_temperatures[celebrity_id] = 0

        # Get all temperature values for percentile calculation
        all_temps = list(new_temperatures.values())

        # Update celebrity database
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for celebrity_id, temperature in new_temperatures.items():
            # Calculate temperature change
            temp_change = self.calculate_temperature_change(celebrity_id, temperature)

            # Get temperature status
            status = self.get_temperature_status(temperature, all_temps)

            # Initialize celebrity if new
            if celebrity_id not in self.celebrities:
                self.celebrities[celebrity_id] = {
                    'discovery_date': now[:10],
                    'promotion_date': now[:10],
                    'memorial': False
                }

            # Update temperature data
            self.celebrities[celebrity_id].update({
                'drama_score': temperature,
                'status': status,
                'last_temperature_update': now,
                'temperature_change': temp_change
            })

            # Set category if missing
            if 'category' not in self.celebrities[celebrity_id]:
                self.celebrities[celebrity_id]['category'] = 'unknown'

        # Add metadata
        self.celebrities['_temperature_metadata'] = {
            'last_calculation': now,
            'calculation_method': 'relative_percentile',
            'lookback_days': self.lookback_days,
            'total_active_celebrities': len([c for c in self.celebrities if c != '_temperature_metadata']),
            'average_temperature': round(statistics.mean(all_temps) if all_temps else 0, 1),
            'median_temperature': round(statistics.median(all_temps) if all_temps else 0, 1),
            'temperature_distribution': self.get_temperature_distribution(all_temps),
            'hottest_celebrities': self.get_hottest_celebrities(new_temperatures),
            'biggest_temperature_changes': self.get_biggest_changes(new_temperatures)
        }

        # Save updated database
        self.save_celebrities()

        print(f"✅ Updated temperatures for {len(new_temperatures)} celebrities")
        print(f"🔥 Average temperature: {self.celebrities['_temperature_metadata']['average_temperature']}")

        return new_temperatures

    def get_temperature_distribution(self, temperatures):
        """Get distribution of temperature statuses"""
        distribution = defaultdict(int)

        for temp in temperatures:
            status = self.get_temperature_status(temp, temperatures)
            distribution[status] += 1

        return dict(distribution)

    def get_hottest_celebrities(self, temperatures, limit=5):
        """Get the hottest celebrities"""
        sorted_temps = sorted(temperatures.items(), key=lambda x: x[1], reverse=True)
        return [[name, temp] for name, temp in sorted_temps[:limit]]

    def get_biggest_changes(self, temperatures, limit=5):
        """Get biggest temperature changes"""
        changes = {}

        for celebrity_id, temp in temperatures.items():
            if celebrity_id in self.celebrities:
                change = self.calculate_temperature_change(celebrity_id, temp)
                changes[celebrity_id] = change

        rising = sorted([(k, v) for k, v in changes.items() if v > 0], 
                       key=lambda x: x[1], reverse=True)[:limit]
        falling = sorted([(k, v) for k, v in changes.items() if v < 0], 
                        key=lambda x: x[1])[:limit]

        return {
            'rising': [[name, change] for name, change in rising],
            'falling': [[name, change] for name, change in falling]
        }

    def save_celebrities(self):
        """Save updated celebrity database"""
        celebrities_file = self.data_dir / 'celebrities.yml'
        with open(celebrities_file, 'w') as f:
            yaml.dump(self.celebrities, f, default_flow_style=False, sort_keys=True)

def main():
    """Main execution function"""
    calculator = TemperatureCalculator()
    temperatures = calculator.update_celebrity_temperatures()

    print("\n🌡️  Temperature Calculation Complete!")
    print("=" * 50)

    # Show top results
    metadata = calculator.celebrities.get('_temperature_metadata', {})

    if 'hottest_celebrities' in metadata:
        print("\n🔥 HOTTEST CELEBRITIES:")
        for name, temp in metadata['hottest_celebrities']:
            print(f"   {name}: {temp}°")

    if 'biggest_temperature_changes' in metadata:
        print("\n📈 BIGGEST RISERS:")
        for name, change in metadata['biggest_temperature_changes'].get('rising', []):
            print(f"   {name}: +{change}°")

        print("\n📉 BIGGEST FALLERS:")
        for name, change in metadata['biggest_temperature_changes'].get('falling', []):
            print(f"   {name}: {change}°")

if __name__ == '__main__':
    main()
