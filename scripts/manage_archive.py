#!/usr/bin/env python3
"""
Archive Manager - Clean up old posts and maintain site performance
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
import shutil

def manage_existing_posts():
    """Clean up existing 1145 posts and keep only the hottest"""

    posts_dir = Path('_posts')
    archive_dir = Path('_archive')
    archive_dir.mkdir(exist_ok=True)

    # Load celebrity data for temperature calculation
    with open('_data/celebrities.yml', 'r') as f:
        celebrities = yaml.safe_load(f) or {}

    posts_with_temp = []

    # Calculate temperature for all existing posts
    for post_file in posts_dir.glob('*.md'):
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])

                    # Calculate temperature
                    drama_score = front_matter.get('drama_score', 0)
                    mentions = front_matter.get('mentions', {})

                    celebrity_boost = 0
                    if mentions:
                        for celeb_key, mention_count in mentions.items():
                            celeb_temp = celebrities.get(celeb_key, {}).get('drama_score', 0)
                            celebrity_boost += celeb_temp * mention_count
                        celebrity_boost = celebrity_boost / len(mentions)

                    temperature = min(100, int(drama_score + (celebrity_boost * 0.6)))

                    posts_with_temp.append({
                        'file': post_file,
                        'temperature': temperature,
                        'drama_score': drama_score,
                        'date': front_matter.get('date', datetime.now())
                    })

        except Exception as e:
            print(f"Error processing {post_file}: {e}")

    # Sort by temperature and keep only top 200 hottest
    posts_with_temp.sort(key=lambda x: x['temperature'], reverse=True)

    keep_posts = posts_with_temp[:200]  # Keep top 200
    archive_posts = posts_with_temp[200:]  # Archive the rest

    print(f"📊 Analysis complete:")
    print(f"   Total posts: {len(posts_with_temp)}")
    print(f"   Keeping: {len(keep_posts)} hottest posts")
    print(f"   Archiving: {len(archive_posts)} cooler posts")

    # Archive the cooler posts
    archived_count = 0
    for post_data in archive_posts:
        post_file = post_data['file']
        archive_path = archive_dir / post_file.name
        shutil.move(str(post_file), str(archive_path))
        archived_count += 1

    print(f"✅ Archived {archived_count} posts")
    print(f"🔥 Kept {len(keep_posts)} hottest posts in _posts/")

    # Show temperature distribution of kept posts
    temp_ranges = {
        'Nuclear (80-100°)': len([p for p in keep_posts if p['temperature'] >= 80]),
        'Explosive (60-79°)': len([p for p in keep_posts if 60 <= p['temperature'] < 80]),
        'Hot (40-59°)': len([p for p in keep_posts if 40 <= p['temperature'] < 60]),
        'Rising (25-39°)': len([p for p in keep_posts if 25 <= p['temperature'] < 40]),
        'Cool (<25°)': len([p for p in keep_posts if p['temperature'] < 25])
    }

    print("\n🌡️ Temperature distribution of kept posts:")
    for range_name, count in temp_ranges.items():
        print(f"   {range_name}: {count} posts")

if __name__ == "__main__":
    manage_existing_posts()
