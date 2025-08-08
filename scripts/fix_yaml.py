#!/usr/bin/env python3
"""
Remove quotes from YAML tags AND fix broken URLs
"""

from pathlib import Path
import re

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing YAML tags and URLs...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix quoted tags
        if "tags: ['" in content:
            content = content.replace("tags: ['", "tags: [")
            content = content.replace("', '", ", ")
            content = content.replace("']", "]")

        # Fix quoted mentions
        if "mentions: {'" in content:
            content = content.replace("mentions: {'", "mentions: {")
            content = content.replace("': ", ": ")
            content = content.replace("'}", "}")

        # Fix broken URLs with spaces
        content = re.sub(r'source_url: "([^"]*) =([^"]*)"', r'source_url: "\1&\2"', content)
        content = re.sub(r'source_url: "([^"]*) _([^"]*)"', r'source_url: "\1&\2"', content)

        if content != original_content:
            print(f"📝 Fixed: {post_file.name}")
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_count += 1

    print(f"🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
