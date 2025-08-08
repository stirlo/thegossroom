#!/usr/bin/env python3
"""
Fix YAML tags - remove quotes from array items
"""

import re
from pathlib import Path

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

    # Fix tags with single quotes
    front_matter = re.sub(
        r"tags: \[([^\]]+)\]",
        lambda m: f"tags: [{re.sub(r\"'([^']+)'\", r'\\1', m.group(1))}]",
        front_matter
    )

    # Fix tags with double quotes  
    front_matter = re.sub(
        r"tags: \[([^\]]+)\]",
        lambda m: f"tags: [{re.sub(r'\"([^\"]+)\"', r'\\1', m.group(1))}]",
        front_matter
    )

    # Fix mentions dictionary quotes
    front_matter = re.sub(
        r"mentions: \{([^}]+)\}",
        lambda m: f"mentions: {{{m.group(1).replace('\"', '').replace(\"'\", '')}}}",
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
