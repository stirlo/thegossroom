#!/usr/bin/env python3
"""
Drama Temperature Calculator
Dynamically calculates relative drama scores based on current activity
"""

import yaml
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import argparse

class DramaTemperatureCalculator:
    def __init__(self):
        self.base_path = Path.cwd()
        self.posts_dir = self.base_path / '_posts'
        self.data_dir = self.base_path / '_data'

        self.load_celebrities()

        # Temperature calculation settings
        self.lookback_days = 30  # How far back to analyze
        self.recency_weight = 2.0  # Weight recent activity higher
        self.velocity_weight = 1.5  # Weight trending activity

    def load_celebrities(self):
        """Load celebrity data"""
        celebrities_file = self.data_dir / 'celebrities.yml'
        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                self.celebrities = yaml.safe_load(f) or {}
        else:
            self.celebrities = {}

    def calculate_all_temperatures(self):
        """Calculate drama temperatures for all celebrities"""
        print("🌡️ Calculating dynamic drama temperatures...")

        # Analyze recent activity
        activity_data = self.analyze_recent_activity()

        # Calculate raw scores
        raw_scores = self.calculate_raw_scores(activity_data)

        # Convert to temperature scale
        temperature_scores = self.convert_to_temperature_scale(raw_scores)

        # Update celebrity data
        self.update_celebrity_temperatures(temperature_scores)

        # Generate temperature report
        self.generate_temperature_report(temperature_scores, activity_data)

        print("✅ Drama temperatures updated!")

    def analyze_recent_activity(self):
        """Analyze recent posting activity for all celebrities"""
        print("📊 Analyzing recent activity...")

        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
        activity_data = defaultdict(lambda: {
            'mentions': 0,
            'total_drama': 0,
            'recent_posts': [],
            'velocity': 0,
            'peak_drama': 0,
            'consistency': 0
        })

        # Analyze posts by week to calculate velocity
        weekly_mentions = defaultdict(lambda: defaultdict(int))

        for post_file in self.posts_dir.glob('*.md'):
            try:
                # Extract date from filename
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', post_file.name)
                if not date_match:
                    continue

                post_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                if post_date < cutoff_date:
                    continue

                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])

                        drama_score = front_matter.get('drama_score', 0)
                        primary_celebrity = front_matter.get('primary_celebrity')
                        tags = front_matter.get('tags', [])

                        # Calculate recency multiplier (more recent = higher weight)
                        days_ago = (datetime.now() - post_date).days
                        recency_multiplier = max(0.1, 1.0 - (days_ago / self.lookback_days))
                        recency_multiplier = recency_multiplier ** (1/self.recency_weight)

                        # Week number for velocity calculation
                        week_num = post_date.isocalendar()[1]

                        # Track primary celebrity
                        if primary_celebrity and primary_celebrity in self.celebrities:
                            weighted_drama = drama_score * recency_multiplier
                            activity_data[primary_celebrity]['mentions'] += 1
                            activity_data[primary_celebrity]['total_drama'] += weighted_drama
                            activity_data[primary_celebrity]['recent_posts'].append({
                                'date': post_date,
                                'drama': drama_score,
                                'weighted_drama': weighted_drama
                            })
                            activity_data[primary_celebrity]['peak_drama'] = max(
                                activity_data[primary_celebrity]['peak_drama'], 
                                drama_score
                            )

                            weekly_mentions[primary_celebrity][week_num] += 1

                        # Track mentioned celebrities in tags
                        for tag in tags:
                            if tag in self.celebrities and tag != primary_celebrity:
                                weighted_drama = drama_score * recency_multiplier * 0.5  # Secondary mention
                                activity_data[tag]['mentions'] += 0.5  # Partial mention
                                activity_data[tag]['total_drama'] += weighted_drama
                                activity_data[tag]['recent_posts'].append({
                                    'date': post_date,
                                    'drama': drama_score * 0.5,
                                    'weighted_drama': weighted_drama
                                })

                                weekly_mentions[tag][week_num] += 0.5

            except Exception as e:
                print(f"❌ Error processing {post_file}: {e}")

        # Calculate velocity (trending up/down)
        for celebrity, weeks in weekly_mentions.items():
            if len(weeks) >= 2:
                week_values = list(weeks.values())
                recent_weeks = week_values[-2:]  # Last 2 weeks
                older_weeks = week_values[:-2] if len(week_values) > 2 else [0]

                recent_avg = sum(recent_weeks) / len(recent_weeks)
                older_avg = sum(older_weeks) / len(older_weeks) if older_weeks else 0

                if older_avg > 0:
                    velocity = (recent_avg - older_avg) / older_avg
                else:
                    velocity = 1.0 if recent_avg > 0 else 0

                activity_data[celebrity]['velocity'] = velocity

        # Calculate consistency (how evenly spread the mentions are)
        for celebrity, data in activity_data.items():
            if data['mentions'] > 1:
                post_dates = [post['date'] for post in data['recent_posts']]
                if len(post_dates) > 1:
                    # Calculate standard deviation of time gaps
                    gaps = []
                    for i in range(1, len(post_dates)):
                        gap = (post_dates[i] - post_dates[i-1]).days
                        gaps.append(gap)

                    if gaps:
                        consistency = 1.0 / (1.0 + statistics.stdev(gaps) / 7)  # Normalize by week
                        activity_data[celebrity]['consistency'] = consistency

        return dict(activity_data)

    def calculate_raw_scores(self, activity_data):
        """Calculate raw drama scores based on activity"""
        print("🔢 Calculating raw drama scores...")

        raw_scores = {}

        for celebrity, data in activity_data.items():
            if data['mentions'] == 0:
                raw_scores[celebrity] = 0
                continue

            # Base score from weighted drama
            base_score = data['total_drama'] / max(1, data['mentions'])

            # Mention frequency bonus
            mention_bonus = min(50, data['mentions'] * 5)  # Cap at 50

            # Velocity bonus/penalty
            velocity_bonus = data['velocity'] * 20 * self.velocity_weight

            # Peak drama bonus
            peak_bonus = min(30, data['peak_drama'] / 10)  # Cap at 30

            # Consistency bonus
            consistency_bonus = data['consistency'] * 15

            # Calculate final raw score
            raw_score = (
                base_score + 
                mention_bonus + 
                velocity_bonus + 
                peak_bonus + 
                consistency_bonus
            )

            raw_scores[celebrity] = max(0, raw_score)  # Ensure non-negative

        return raw_scores

    def convert_to_temperature_scale(self, raw_scores):
        """Convert raw scores to 0-100 temperature scale"""
        print("🌡️ Converting to temperature scale...")

        if not raw_scores:
            return {}

        # Get score distribution
        scores = list(raw_scores.values())
        scores = [s for s in scores if s > 0]  # Remove zeros for percentile calculation

        if not scores:
            return {celebrity: 0 for celebrity in raw_scores}

        # Calculate percentiles
        scores.sort()

        def get_percentile_value(percentile):
            if len(scores) == 1:
                return scores[0]
            index = (percentile / 100) * (len(scores) - 1)
            lower_index = int(index)
            upper_index = min(lower_index + 1, len(scores) - 1)
            weight = index - lower_index
            return scores[lower_index] * (1 - weight) + scores[upper_index] * weight

        # Define temperature thresholds based on percentiles
        p95 = get_percentile_value(95)  # 100° (Explosive)
        p85 = get_percentile_value(85)  # 70° (Hot)
        p70 = get_percentile_value(70)  # 50° (Rising)
        p50 = get_percentile_value(50)  # 30° (Mild)
        p25 = get_percentile_value(25)  # 10° (Cooling)

        temperature_scores = {}

        for celebrity, raw_score in raw_scores.items():
            if raw_score == 0:
                temperature = 0
            elif raw_score >= p95:
                # 70-100° range (Hot to Explosive)
                temperature = 70 + (30 * (raw_score - p85) / max(1, p95 - p85))
                temperature = min(100, temperature)
            elif raw_score >= p85:
                # 50-70° range (Rising to Hot)
                temperature = 50 + (20 * (raw_score - p70) / max(1, p85 - p70))
            elif raw_score >= p70:
                # 30-50° range (Mild to Rising)
                temperature = 30 + (20 * (raw_score - p50) / max(1, p70 - p50))
            elif raw_score >= p50:
                # 10-30° range (Cooling to Mild)
                temperature = 10 + (20 * (raw_score - p25) / max(1, p50 - p25))
            else:
                # 0-10° range (Freezing to Cooling)
                temperature = 10 * (raw_score / max(1, p25))

            temperature_scores[celebrity] = round(max(0, min(100, temperature)), 1)

        return temperature_scores

    def update_celebrity_temperatures(self, temperature_scores):
        """Update celebrity data with new temperatures"""
        print("📝 Updating celebrity temperatures...")

        updated_count = 0

        for celebrity, temperature in temperature_scores.items():
            if celebrity in self.celebrities:
                old_score = self.celebrities[celebrity].get('drama_score', 0)
                self.celebrities[celebrity]['drama_score'] = temperature
                self.celebrities[celebrity]['last_temperature_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Update status based on temperature
                if temperature >= 70:
                    status = 'explosive' if temperature >= 85 else 'hot'
                elif temperature >= 50:
                    status = 'rising'
                elif temperature >= 30:
                    status = 'mild'
                elif temperature >= 10:
                    status = 'cooling'
                else:
                    status = 'freezing'

                self.celebrities[celebrity]['status'] = status

                # Track temperature change
                if old_score > 0:
                    change = temperature - old_score
                    self.celebrities[celebrity]['temperature_change'] = round(change, 1)

                updated_count += 1

        # Set inactive celebrities to freezing
        for celebrity, data in self.celebrities.items():
            if celebrity not in temperature_scores and data.get('status') != 'memorial':
                self.celebrities[celebrity]['drama_score'] = 0
                self.celebrities[celebrity]['status'] = 'freezing'
                self.celebrities[celebrity]['temperature_change'] = -data.get('drama_score', 0)
                updated_count += 1

        # Save updated data
        self.save_celebrities()
        print(f"✅ Updated {updated_count} celebrity temperatures")

    def generate_temperature_report(self, temperature_scores, activity_data):
        """Generate a temperature report"""
        print("📊 Generating temperature report...")

        # Sort by temperature
        sorted_temps = sorted(temperature_scores.items(), key=lambda x: x[1], reverse=True)

        report = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_celebrities': len(temperature_scores),
            'temperature_distribution': {
                'explosive': len([t for _, t in sorted_temps if t >= 85]),
                'hot': len([t for _, t in sorted_temps if 70 <= t < 85]),
                'rising': len([t for _, t in sorted_temps if 50 <= t < 70]),
                'mild': len([t for _, t in sorted_temps if 30 <= t < 50]),
                'cooling': len([t for _, t in sorted_temps if 10 <= t < 30]),
                'freezing': len([t for _, t in sorted_temps if t < 10])
            },
            'hottest_celebrities': sorted_temps[:10],
            'biggest_risers': [],
            'biggest_fallers': []
        }

        # Find biggest changes
        changes = []
        for celebrity, data in self.celebrities.items():
            change = data.get('temperature_change', 0)
            if abs(change) > 0:
                changes.append((celebrity, change))

        changes.sort(key=lambda x: x[1], reverse=True)
        report['biggest_risers'] = changes[:5]
        report['biggest_fallers'] = changes[-5:]

        # Save report
        with open(self.data_dir / 'temperature_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n🌡️ DRAMA TEMPERATURE REPORT")
        print("=" * 40)
        print(f"🔥 Explosive (85-100°): {report['temperature_distribution']['explosive']}")
        print(f"🌶️ Hot (70-84°): {report['temperature_distribution']['hot']}")
        print(f"📈 Rising (50-69°): {report['temperature_distribution']['rising']}")
        print(f"😐 Mild (30-49°): {report['temperature_distribution']['mild']}")
        print(f"❄️ Cooling (10-29°): {report['temperature_distribution']['cooling']}")
        print(f"🧊 Freezing (0-9°): {report['temperature_distribution']['freezing']}")
        print("\n🔥 HOTTEST RIGHT NOW:")
        for celebrity, temp in sorted_temps[:5]:
            print(f"   {celebrity.replace('_', ' ').title()}: {temp}°")
        print("=" * 40)

    def save_celebrities(self):
        """Save updated celebrity data"""
        with open(self.data_dir / 'celebrities.yml', 'w') as f:
            f.write("# Celebrity Drama Tracking Database\n")
            f.write("# Auto-updated by discovery scripts and manual additions\n")
            f.write("# Drama scores are relative temperatures (0-100°)\n\n")
            yaml.dump(self.celebrities, f, default_flow_style=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Drama Temperature Calculator')
    parser.add_argument('action', choices=['calculate'], 
                       help='Action to perform')

    args = parser.parse_args()

    calculator = DramaTemperatureCalculator()

    if args.action == 'calculate':
        calculator.calculate_all_temperatures()
