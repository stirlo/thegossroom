#!/usr/bin/env python3
"""
EMERGENCY: Immediate cleanup of 1145+ posts to get site building again
This will drastically reduce posts to only the hottest content
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import re

class EmergencyCleanup:
    def __init__(self):
        self.base_path = Path('.')
        self.posts_dir = self.base_path / '_posts'
        self.archive_dir = self.base_path / '_archive'
        self.cold_storage_dir = self.base_path / '_cold_storage'

        # Create directories
        self.archive_dir.mkdir(exist_ok=True)
        self.cold_storage_dir.mkdir(exist_ok=True)

        self.celebrities = self.load_celebrities()

    def load_celebrities(self):
        try:
            with open(self.base_path / '_data' / 'celebrities.yml', 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def calculate_emergency_temperature(self, front_matter):
        """Quick temperature calculation for emergency cleanup"""
        drama_score = front_matter.get('drama_score', 0)
        mentions = front_matter.get('mentions', {})

        # Celebrity boost
        celebrity_boost = 0
        if mentions:
            for celeb_key, mention_count in mentions.items():
                celeb_temp = self.celebrities.get(celeb_key, {}).get('drama_score', 50)
                celebrity_boost += celeb_temp * mention_count
            celebrity_boost = celebrity_boost / len(mentions) if mentions else 0

        # Age penalty (older posts get cooler)
        post_date = front_matter.get('date')
        age_penalty = 0

        if isinstance(post_date, str):
            try:
                post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                days_old = (datetime.now() - post_datetime.replace(tzinfo=None)).days

                if days_old > 30:
                    age_penalty = 20
                elif days_old > 14:
                    age_penalty = 10
                elif days_old > 7:
                    age_penalty = 5
            except:
                age_penalty = 15  # Unknown date = penalty

        temperature = drama_score + (celebrity_boost * 0.4) - age_penalty
        return max(0, min(100, int(temperature)))

    def emergency_cleanup(self):
        """NUCLEAR OPTION: Keep only the absolute hottest posts"""

        print("🚨 EMERGENCY CLEANUP STARTING...")
        print("🚨 This will DRASTICALLY reduce your posts to get the site building!")

        all_posts = []
        total_files = len(list(self.posts_dir.glob('*.md')))
        print(f"📊 Found {total_files} posts to analyze...")

        # Analyze all posts
        for i, post_file in enumerate(self.posts_dir.glob('*.md'), 1):
            if i % 100 == 0:
                print(f"   Analyzed {i}/{total_files} posts...")

            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.startswith('---'):
                    continue

                parts = content.split('---', 2)
                if len(parts) < 2:
                    continue

                front_matter = yaml.safe_load(parts[1])

                # Extract date from filename
                try:
                    if post_file.name.startswith('20'):
                        file_date = datetime.strptime(post_file.name[:10], '%Y-%m-%d')
                    else:
                        file_date = datetime.now() - timedelta(days=365)  # Very old
                except:
                    file_date = datetime.now() - timedelta(days=365)

                temperature = self.calculate_emergency_temperature(front_matter)
                days_old = (datetime.now() - file_date).days

                all_posts.append({
                    'file': post_file,
                    'filename': post_file.name,
                    'title': front_matter.get('title', 'Untitled')[:50],
                    'temperature': temperature,
                    'drama_score': front_matter.get('drama_score', 0),
                    'days_old': days_old,
                    'primary_celebrity': front_matter.get('primary_celebrity', ''),
                    'file_size': post_file.stat().st_size
                })

            except Exception as e:
                print(f"⚠️ Error analyzing {post_file}: {e}")
                continue

        print(f"✅ Analyzed {len(all_posts)} posts")

        # Sort by temperature (hottest first)
        all_posts.sort(key=lambda x: (-x['temperature'], -x['drama_score'], x['days_old']))

        # AGGRESSIVE FILTERING
        keep_active = []
        keep_archive = []
        cold_storage = []

        for post in all_posts:
            # Keep active: Only the absolute hottest (temp >= 60 OR top 50)
            if post['temperature'] >= 60 or len(keep_active) < 50:
                keep_active.append(post)
            # Keep in archive: Warm posts (temp >= 35 OR top 150 total)
            elif post['temperature'] >= 35 or len(keep_active) + len(keep_archive) < 150:
                keep_archive.append(post)
            # Everything else goes to cold storage
            else:
                cold_storage.append(post)

        print(f"\n🎯 EMERGENCY PLAN:")
        print(f"   🔥 Keep ACTIVE: {len(keep_active)} posts (temp >= 60° or top 50)")
        print(f"   📦 Keep ARCHIVED: {len(keep_archive)} posts (temp >= 35° or top 150)")
        print(f"   🧊 COLD STORAGE: {len(cold_storage)} posts (everything else)")

        # Show temperature breakdown of what we're keeping
        active_temps = [p['temperature'] for p in keep_active]
        archive_temps = [p['temperature'] for p in keep_archive]

        if active_temps:
            print(f"   🔥 Active temp range: {min(active_temps)}° - {max(active_temps)}°")
        if archive_temps:
            print(f"   📦 Archive temp range: {min(archive_temps)}° - {max(archive_temps)}°")

        # Confirm before proceeding
        response = input(f"\n⚠️  This will move {len(cold_storage)} posts to cold storage. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Emergency cleanup cancelled")
            return

        # Execute the moves
        print("\n🚀 Executing emergency cleanup...")

        moved_to_archive = 0
        moved_to_cold = 0

        # Move posts to archive
        for post in keep_archive:
            archive_path = self.archive_dir / post['filename']
            if not archive_path.exists():
                shutil.move(str(post['file']), str(archive_path))
                moved_to_archive += 1

        # Move posts to cold storage
        for post in cold_storage:
            cold_path = self.cold_storage_dir / post['filename']
            if not cold_path.exists():
                shutil.move(str(post['file']), str(cold_path))
                moved_to_cold += 1

        print(f"✅ Emergency cleanup complete!")
        print(f"   🔥 Active posts: {len(keep_active)}")
        print(f"   📦 Moved to archive: {moved_to_archive}")
        print(f"   🧊 Moved to cold storage: {moved_to_cold}")

        # Show the hottest posts we kept
        print(f"\n🔥 TOP 10 HOTTEST POSTS KEPT ACTIVE:")
        for i, post in enumerate(keep_active[:10], 1):
            print(f"   {i:2d}. {post['title']} (🌡️{post['temperature']}°)")

        # Create summary report
        summary = {
            'cleanup_date': datetime.now().isoformat(),
            'original_count': total_files,
            'kept_active': len(keep_active),
            'moved_to_archive': moved_to_archive,
            'moved_to_cold_storage': moved_to_cold,
            'active_temp_range': f"{min(active_temps) if active_temps else 0}° - {max(active_temps) if active_temps else 0}°",
            'archive_temp_range': f"{min(archive_temps) if archive_temps else 0}° - {max(archive_temps) if archive_temps else 0}°"
        }

        with open('data/emergency_cleanup_report.json', 'w') as f:
            import json
            json.dump(summary, f, indent=2)

        print(f"\n📊 Report saved to data/emergency_cleanup_report.json")
        print(f"🚀 Your site should now build much faster with only {len(keep_active)} active posts!")

    def quick_stats(self):
        """Show quick stats without moving anything"""
        posts = list(self.posts_dir.glob('*.md'))
        print(f"📊 Current stats:")
        print(f"   Posts in _posts/: {len(posts)}")
        print(f"   Posts in _archive/: {len(list(self.archive_dir.glob('*.md')))}")
        print(f"   Posts in _cold_storage/: {len(list(self.cold_storage_dir.glob('*.md')))}")

        # Quick temperature sample
        sample_temps = []
        for post_file in posts[:50]:  # Sample first 50
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        front_matter = yaml.safe_load(parts[1])
                        temp = self.calculate_emergency_temperature(front_matter)
                        sample_temps.append(temp)
            except:
                continue

        if sample_temps:
            avg_temp = sum(sample_temps) / len(sample_temps)
            print(f"   Sample average temperature: {avg_temp:.1f}°")
            print(f"   Sample temp range: {min(sample_temps)}° - {max(sample_temps)}°")

if __name__ == "__main__":
    cleanup = EmergencyCleanup()

    print("🚨 EMERGENCY CLEANUP TOOL")
    print("=" * 50)

    # Show current stats
    cleanup.quick_stats()

    print("\nOptions:")
    print("1. Run emergency cleanup (AGGRESSIVE)")
    print("2. Just show stats")
    print("3. Exit")

    choice = input("\nChoose option (1-3): ")

    if choice == "1":
        cleanup.emergency_cleanup()
    elif choice == "2":
        cleanup.quick_stats()
    else:
        print("👋 Goodbye!")
