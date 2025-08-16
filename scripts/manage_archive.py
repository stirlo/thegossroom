#!/usr/bin/env python3
"""
Intelligent Archive Manager - Runs weekly with different cleanup strategies
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json
import argparse

class IntelligentArchiveManager:
    def __init__(self):
        self.base_path = Path('.')
        self.posts_dir = self.base_path / '_posts'
        self.archive_dir = self.base_path / '_archive'
        self.cold_storage_dir = self.base_path / '_cold_storage'

        # Create directories
        self.archive_dir.mkdir(exist_ok=True)
        self.cold_storage_dir.mkdir(exist_ok=True)

        self.celebrities = self.load_celebrities()

        # Archive thresholds
        self.MAX_ACTIVE_POSTS = 200      # Keep in _posts/
        self.MAX_ARCHIVE_POSTS = 500     # Keep in _archive/
        self.MIN_TEMPERATURE_KEEP = 30   # Don't archive posts above this temp
        self.ARCHIVE_AFTER_DAYS = 14     # Archive posts older than 2 weeks
        self.COLD_STORAGE_AFTER_DAYS = 90 # Cold storage after 3 months

    def load_celebrities(self):
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def calculate_post_temperature(self, front_matter):
        """Calculate current temperature for a post"""
        drama_score = front_matter.get('drama_score', 0)
        mentions = front_matter.get('mentions', {})

        # Get current celebrity temperatures
        celebrity_boost = 0
        if mentions:
            total_celeb_temp = 0
            for celeb_key, mention_count in mentions.items():
                current_celeb_temp = self.celebrities.get(celeb_key, {}).get('drama_score', 0)
                total_celeb_temp += current_celeb_temp * mention_count
            celebrity_boost = total_celeb_temp / len(mentions) if mentions else 0

        # Time decay factor
        post_date = front_matter.get('date')
        if isinstance(post_date, str):
            try:
                post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                days_old = (datetime.now() - post_datetime.replace(tzinfo=None)).days

                if days_old < 1:
                    time_factor = 1.0
                elif days_old < 7:
                    time_factor = 0.9
                elif days_old < 30:
                    time_factor = 0.7
                elif days_old < 90:
                    time_factor = 0.4
                else:
                    time_factor = 0.1
            except:
                time_factor = 0.5
        else:
            time_factor = 0.5

        temperature = (drama_score + (celebrity_boost * 0.6)) * time_factor
        return min(100, int(temperature))

    def analyze_all_posts(self):
        """Analyze all posts across _posts/ and _archive/"""
        all_posts = []

        # Analyze active posts
        for post_file in self.posts_dir.glob('*.md'):
            post_data = self.analyze_post(post_file, 'active')
            if post_data:
                all_posts.append(post_data)

        # Analyze archived posts
        for post_file in self.archive_dir.glob('*.md'):
            post_data = self.analyze_post(post_file, 'archived')
            if post_data:
                all_posts.append(post_data)

        return all_posts

    def analyze_post(self, post_file, current_location):
        """Analyze individual post"""
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 2:
                return None

            front_matter = yaml.safe_load(parts[1])

            # Extract date from filename or front matter
            try:
                if post_file.name.startswith('20'):
                    file_date = datetime.strptime(post_file.name[:10], '%Y-%m-%d')
                else:
                    file_date = datetime.now()
            except:
                file_date = datetime.now()

            post_date = front_matter.get('date', file_date)
            if isinstance(post_date, str):
                try:
                    post_date = datetime.fromisoformat(post_date.replace('Z', '+00:00')).replace(tzinfo=None)
                except:
                    post_date = file_date

            temperature = self.calculate_post_temperature(front_matter)
            days_old = (datetime.now() - post_date).days

            return {
                'file': post_file,
                'filename': post_file.name,
                'title': front_matter.get('title', 'Untitled'),
                'temperature': temperature,
                'drama_score': front_matter.get('drama_score', 0),
                'date': post_date,
                'days_old': days_old,
                'current_location': current_location,
                'primary_celebrity': front_matter.get('primary_celebrity', ''),
                'mentions': front_matter.get('mentions', {})
            }

        except Exception as e:
            print(f"⚠️ Error analyzing {post_file}: {e}")
            return None

    def weekly_cleanup(self):
        """Weekly cleanup - gentle archiving"""
        print("🗓️ Running WEEKLY cleanup...")

        all_posts = self.analyze_all_posts()
        print(f"📊 Found {len(all_posts)} total posts")

        # Separate by current location
        active_posts = [p for p in all_posts if p['current_location'] == 'active']
        archived_posts = [p for p in all_posts if p['current_location'] == 'archived']

        print(f"   Active: {len(active_posts)}, Archived: {len(archived_posts)}")

        # Sort all posts by temperature (hottest first)
        all_posts.sort(key=lambda x: (-x['temperature'], -x['date'].timestamp()))

        # Determine what stays active (top posts + recent hot posts)
        keep_active = []
        archive_candidates = []

        for post in all_posts:
            # Always keep posts that are:
            # 1. Very hot (temp >= 50)
            # 2. Recent and warm (< 7 days old and temp >= 30)
            # 3. In top 150 by temperature

            if (post['temperature'] >= 50 or 
                (post['days_old'] < 7 and post['temperature'] >= 30) or
                len(keep_active) < 150):
                keep_active.append(post)
            else:
                archive_candidates.append(post)

        # Limit active posts to MAX_ACTIVE_POSTS
        if len(keep_active) > self.MAX_ACTIVE_POSTS:
            archive_candidates.extend(keep_active[self.MAX_ACTIVE_POSTS:])
            keep_active = keep_active[:self.MAX_ACTIVE_POSTS]

        # Move posts as needed
        moved_to_archive = 0
        for post in archive_candidates:
            if post['current_location'] == 'active':
                self.move_to_archive(post)
                moved_to_archive += 1

        print(f"📦 Moved {moved_to_archive} posts to archive")
        print(f"🔥 Keeping {len(keep_active)} active posts")

        return {
            'moved_to_archive': moved_to_archive,
            'active_posts': len(keep_active),
            'archived_posts': len(archived_posts) + moved_to_archive
        }

    def monthly_deep_clean(self):
        """Monthly deep clean - aggressive cleanup"""
        print("🗓️ Running MONTHLY deep clean...")

        all_posts = self.analyze_all_posts()

        # Sort by temperature
        all_posts.sort(key=lambda x: (-x['temperature'], -x['date'].timestamp()))

        # Aggressive filtering
        keep_active = []
        keep_archived = []
        cold_storage_candidates = []

        for post in all_posts:
            # Keep active: Top 100 hottest + anything above 60° temp
            if post['temperature'] >= 60 or len(keep_active) < 100:
                keep_active.append(post)
            # Keep archived: Next 300 posts or anything above 25° temp
            elif post['temperature'] >= 25 or len(keep_archived) < 300:
                keep_archived.append(post)
            # Everything else goes to cold storage
            else:
                cold_storage_candidates.append(post)

        # Execute moves
        moves = {'to_active': 0, 'to_archive': 0, 'to_cold': 0}

        for post in all_posts:
            current_loc = post['current_location']

            if post in keep_active:
                if current_loc != 'active':
                    self.move_to_active(post)
                    moves['to_active'] += 1
            elif post in keep_archived:
                if current_loc != 'archived':
                    self.move_to_archive(post)
                    moves['to_archive'] += 1
            else:
                self.move_to_cold_storage(post)
                moves['to_cold'] += 1

        print(f"📊 Monthly cleanup complete:")
        print(f"   🔥 Active posts: {len(keep_active)}")
        print(f"   📦 Archived posts: {len(keep_archived)}")
        print(f"   🧊 Cold storage: {len(cold_storage_candidates)}")
        print(f"   Moves - Active: {moves['to_active']}, Archive: {moves['to_archive']}, Cold: {moves['to_cold']}")

        return moves

    def move_to_archive(self, post):
        """Move post to archive"""
        if post['current_location'] == 'active':
            archive_path = self.archive_dir / post['filename']
            shutil.move(str(post['file']), str(archive_path))

    def move_to_active(self, post):
        """Move post back to active"""
        if post['current_location'] == 'archived':
            active_path = self.posts_dir / post['filename']
            shutil.move(str(post['file']), str(active_path))

    def move_to_cold_storage(self, post):
        """Move post to cold storage"""
        cold_path = self.cold_storage_dir / post['filename']
        shutil.move(str(post['file']), str(cold_path))

    def emergency_cleanup(self):
        """Emergency cleanup when build times are too long"""
        print("🚨 Running EMERGENCY cleanup...")

        all_posts = self.analyze_all_posts()
        all_posts.sort(key=lambda x: (-x['temperature'], -x['date'].timestamp()))

        # Keep only top 50 hottest posts active
        keep_active = all_posts[:50]
        archive_rest = all_posts[50:]

        moved = 0
        for post in archive_rest:
            if post['current_location'] == 'active':
                self.move_to_archive(post)
                moved += 1

        print(f"🚨 Emergency cleanup: Kept 50 hottest posts, archived {moved}")
        return moved

    def generate_archive_report(self):
        """Generate archive analytics report"""
        all_posts = self.analyze_all_posts()

        # Temperature distribution
        temp_ranges = {
            'Nuclear (80-100°)': len([p for p in all_posts if p['temperature'] >= 80]),
            'Explosive (60-79°)': len([p for p in all_posts if 60 <= p['temperature'] < 80]),
            'Hot (40-59°)': len([p for p in all_posts if 40 <= p['temperature'] < 60]),
            'Warm (25-39°)': len([p for p in all_posts if 25 <= p['temperature'] < 40]),
            'Cool (<25°)': len([p for p in all_posts if p['temperature'] < 25])
        }

        # Location distribution
        location_dist = {
            'Active': len([p for p in all_posts if p['current_location'] == 'active']),
            'Archived': len([p for p in all_posts if p['current_location'] == 'archived'])
        }

        # Age distribution
        age_ranges = {
            'Today': len([p for p in all_posts if p['days_old'] == 0]),
            'This week': len([p for p in all_posts if 1 <= p['days_old'] <= 7]),
            'This month': len([p for p in all_posts if 8 <= p['days_old'] <= 30]),
            'Older': len([p for p in all_posts if p['days_old'] > 30])
        }

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_posts': len(all_posts),
            'temperature_distribution': temp_ranges,
            'location_distribution': location_dist,
            'age_distribution': age_ranges,
            'hottest_posts': [
                {
                    'title': p['title'][:50] + '...' if len(p['title']) > 50 else p['title'],
                    'temperature': p['temperature'],
                    'days_old': p['days_old'],
                    'location': p['current_location']
                }
                for p in sorted(all_posts, key=lambda x: x['temperature'], reverse=True)[:10]
            ]
        }

        # Save report
        with open('data/archive_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return report

    def run(self, mode='weekly'):
        """Run archive management"""
        print(f"🗂️ Starting Archive Manager in {mode.upper()} mode...")

        if mode == 'weekly':
            result = self.weekly_cleanup()
        elif mode == 'monthly':
            result = self.monthly_deep_clean()
        elif mode == 'emergency':
            result = self.emergency_cleanup()
        else:
            print("❌ Invalid mode. Use: weekly, monthly, or emergency")
            return

        # Generate report
        report = self.generate_archive_report()

        print("\n📊 Archive Report:")
        print(f"   Total posts: {report['total_posts']}")
        print(f"   Active: {report['location_distribution']['Active']}")
        print(f"   Archived: {report['location_distribution']['Archived']}")

        print("\n🌡️ Temperature Distribution:")
        for temp_range, count in report['temperature_distribution'].items():
            print(f"   {temp_range}: {count}")

        print("\n✅ Archive management complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Intelligent Archive Manager')
    parser.add_argument('--mode', choices=['weekly', 'monthly', 'emergency'], 
                       default='weekly', help='Cleanup mode')

    args = parser.parse_args()

    manager = IntelligentArchiveManager()
    manager.run(args.mode)
