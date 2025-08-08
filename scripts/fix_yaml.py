#!/usr/bin/env python3
"""
Fix YAML tags - remove quotes from array items
"""

import re
from pathlib import Path

def remove_quotes_from_tags(match_obj):
    """Remove quotes from tag items"""
    tag_content = match_obj.group(1)
    # Remove single quotes
    tag_content = re.sub(r"'([^']+)'", r'\1', tag_content)
    # Remove double quotes
    tag_content = re.sub(r'"([^"]+)"', r'\1', tag_content)
    return f"tags: [{tag_content}]"

def remove_quotes_from_mentions(match_obj):
    """Remove quotes from mentions dictionary"""
    mentions_content = match_obj.group(1)
    cleaned = mentions_content.replace('"', '').replace("'", '')
    return f"mentions: {{{cleaned}}}"

def fix_yaml_tags(content):
    """Fix quoted tags in YAML front matter"""
    if not content.startswith('---\n'):
        return content

    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return content

    front_matter = parts[1]
    post_content = parts[2]
    original_fm = front_matter

    # Fix tags array - remove quotes from items
    front_matter = re.sub(
        r"tags: \[([^\]]+)\]",
        remove_quotes_from_tags,
        front_matter
    )

    # Fix mentions dictionary - remove quotes
    front_matter = re.sub(
        r"mentions: \{([^}]+)\}",
        remove_quotes_from_mentions,
        front_matter
    )

    if front_matter != original_fm:
        return f"---\n{front_matter}---\n{post_content}"

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing quoted YAML tags...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_yaml_tags(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()