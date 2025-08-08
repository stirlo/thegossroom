#!/usr/bin/env python3
"""
Fix YAML quotes and formatting in Jekyll posts
"""

import re
from pathlib import Path

def fix_yaml_issues(content):
    """Fix YAML syntax issues"""
    if not content.startswith('---\n'):
        return content

    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return content

    front_matter = parts[1]
    post_content = parts[2]
    original_content = content

    # Fix tags: remove quotes from array items
    front_matter = re.sub(
        r"tags: \[([^\]]+)\]",
        lambda m: f"tags: [{re.sub(r\"'([^']+)'\", r'\\1', m.group(1))}]",
        front_matter
    )

    # Fix mentions: remove quotes from dictionary keys
    front_matter = re.sub(
        r"mentions: \{([^}]+)\}",
        lambda m: f"mentions: {{{re.sub(r\"'([^']+)'\", r'\\1', m.group(1))}}}",
        front_matter
    )

    # Reconstruct content
    fixed_content = f"---\n{front_matter}---\n{post_content}"

    return fixed_content if fixed_content != original_content else content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing YAML quotes in Jekyll posts...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_yaml_issues(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
