#!/usr/bin/env python3
"""
Fix YAML quotes and formatting in Jekyll posts
"""

import re
from pathlib import Path

def remove_quotes_from_tags(tag_content):
    """Remove quotes from tag items"""
    return re.sub(r"'([^']+)'", r'\1', tag_content)

def remove_quotes_from_mentions(mentions_content):
    """Remove quotes from mentions keys"""
    return re.sub(r"'([^']+)'", r'\1', mentions_content)

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
    def fix_tags_match(match):
        tag_content = match.group(1)
        clean_tags = remove_quotes_from_tags(tag_content)
        return f"tags: [{clean_tags}]"

    front_matter = re.sub(r"tags: \[([^\]]+)\]", fix_tags_match, front_matter)

    # Fix mentions: remove quotes from dictionary keys
    def fix_mentions_match(match):
        mentions_content = match.group(1)
        clean_mentions = remove_quotes_from_mentions(mentions_content)
        return f"mentions: {{{clean_mentions}}}"

    front_matter = re.sub(r"mentions: \{([^}]+)\}", fix_mentions_match, front_matter)

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
