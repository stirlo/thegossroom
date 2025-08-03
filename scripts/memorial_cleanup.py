#!/usr/bin/env python3
"""
Memorial Cleanup Script - Removes celebrities from memorial after 18 months
"""

import yaml
import os
from pathlib import Path
from datetime import datetime, timedelta
import re

class MemorialCleanup:
    def __init__(self):
        self.base_path = Path.cwd()
        self.eighteen_months = timedelta(days=547)  # 18 months in days

    def cleanup_memorial_celebrities(self):
        """Remove celebrities from memorial status after 18 months"""
        celebrities_file = self.base_path / '_data' / 'celebrities.yml'

        if not celebrities_file.exists():
            print("❌ No celebrities.yml file found")
            return

        # Load celebrities data
        with open(celebrities_file, 'r') as f:
            celebrities = yaml.safe_load(f)

        if not celebrities:
            print("❌ No celebrity data found")
            return

        updated_count = 0
        removed_celebrities = []
        cutoff_date = datetime.now() - self.eighteen_months

        for celebrity_name, celebrity_info in celebrities.items():
            if celebrity_info.get('status') == 'memorial':
                death_date_str = celebrity_info.get('death_date')

                if death_date_str:
                    try:
                        # Parse death date (assuming YYYY-MM-DD format)
                        death_date = datetime.strptime(death_date_str, '%Y-%m-%d')

                        if death_date < cutoff_date:
                            # Remove memorial status
                            celebrity_info['status'] = 'inactive'
                            celebrity_info['memorial_note'] = f"Remembered (removed {datetime.now().strftime('%Y-%m-%d')})"
                            celebrity_info['drama_score'] = 0  # Set to 0 so they don't appear in active categories

                            updated_count += 1
                            removed_celebrities.append({
                                'name': celebrity_name,
                                'death_date': death_date_str,
                                'months_ago': (datetime.now() - death_date).days // 30
                            })

                            print(f"🕊️ Moved {celebrity_name} from memorial (died {death_date_str})")

                    except ValueError:
                        print(f"⚠️ Invalid death date format for {celebrity_name}: {death_date_str}")

        if updated_count > 0:
            # Save updated celebrities data
            with open(celebrities_file, 'w') as f:
                yaml.dump(celebrities, f, default_flow_style=False, sort_keys=True)

            print(f"\n✅ Updated {updated_count} memorial celebrities")

            # Also clean up posts - remove memorial tag from old posts
            self.cleanup_memorial_tags(removed_celebrities)
        else:
            print("📭 No memorial celebrities need cleanup")

    def cleanup_memorial_tags(self, removed_celebrities):
        """Remove memorial tags from posts of celebrities no longer in memorial"""
        posts_dir = self.base_path / '_posts'
        if not posts_dir.exists():
            return

        cleaned_posts = 0
        celebrity_names = [celeb['name'].lower() for celeb in removed_celebrities]

        for post_file in posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.startswith('---'):
                    continue

                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue

                front_matter = yaml.safe_load(parts[1])
                post_content = parts[2]

                # Check if this post mentions any removed memorial celebrities
                post_updated = False

                # Remove memorial tag if present
                if 'tags' in front_matter and front_matter['tags']:
                    if 'memorial' in front_matter['tags']:
                        # Check if post is about a removed memorial celebrity
                        primary_celeb = front_matter.get('primary_celebrity', '').lower()
                        post_title = front_matter.get('title', '').lower()

                        for celeb_name in celebrity_names:
                            if celeb_name in primary_celeb or celeb_name.replace('_', ' ') in post_title:
                                front_matter['tags'].remove('memorial')
                                post_updated = True
                                break

                if post_updated:
                    new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                    with open(post_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    cleaned_posts += 1

            except Exception as e:
                print(f"⚠️ Error processing {post_file.name}: {e}")

        if cleaned_posts > 0:
            print(f"🧹 Cleaned memorial tags from {cleaned_posts} posts")

    def show_memorial_status(self):
        """Show current memorial status and upcoming removals"""
        celebrities_file = self.base_path / '_data' / 'celebrities.yml'

        if not celebrities_file.exists():
            print("❌ No celebrities.yml file found")
            return

        with open(celebrities_file, 'r') as f:
            celebrities = yaml.safe_load(f)

        if not celebrities:
            return

        memorial_celebrities = []
        cutoff_date = datetime.now() - self.eighteen_months

        for celebrity_name, celebrity_info in celebrities.items():
            if celebrity_info.get('status') == 'memorial':
                death_date_str = celebrity_info.get('death_date')
                if death_date_str:
                    try:
                        death_date = datetime.strptime(death_date_str, '%Y-%m-%d')
                        months_since = (datetime.now() - death_date).days // 30

                        memorial_celebrities.append({
                            'name': celebrity_name,
                            'death_date': death_date_str,
                            'months_ago': months_since,
                            'will_remove': death_date < cutoff_date
                        })
                    except ValueError:
                        pass

        memorial_celebrities.sort(key=lambda x: x['months_ago'], reverse=True)

        print("\n🕊️ Memorial Status Report:")
        print("=" * 50)

        for celeb in memorial_celebrities:
            status = "🔄 WILL REMOVE" if celeb['will_remove'] else "✅ Active"
            print(f"{celeb['name'].replace('_', ' ').title():<25} | {celeb['death_date']} | {celeb['months_ago']:2d} months | {status}")

        active_memorials = len([c for c in memorial_celebrities if not c['will_remove']])
        removing_count = len([c for c in memorial_celebrities if c['will_remove']])

        print(f"\n📊 Summary:")
        print(f"   Active memorials: {active_memorials}")
        print(f"   Will be removed: {removing_count}")

if __name__ == "__main__":
    import sys

    cleanup = MemorialCleanup()

    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            cleanup.show_memorial_status()
        elif sys.argv[1] == "cleanup":
            cleanup.cleanup_memorial_celebrities()
        else:
            print("Usage: python memorial_cleanup.py [status|cleanup]")
    else:
        cleanup.show_memorial_status()
