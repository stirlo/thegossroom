#!/usr/bin/env python3
"""
Fix ALL post formatting issues to make them perfect
"""

import re
from pathlib import Path

def fix_all_post_issues(content):
    """Fix every formatting issue we've identified"""

    # Fix 1: Missing closing quotes in titles
    content = re.sub(r'title: "([^"]*)\n', r'title: "\1"\n', content)

    # Fix 2: Extra quotes in source lines
    content = re.sub(r'source: ([^"]+)"\n', r'source: \1\n', content)

    # Fix 3: Ensure blank line after front matter closing ---
    content = re.sub(r'---\n([A-Z])', r'---\n\n\1', content)
    content = re.sub(r'---\n([a-z])', r'---\n\n\1', content)

    # Fix 4: Fix broken URLs with spaces
    content = re.sub(r'=1490 _campaign=1490', r'&ns_campaign=1490', content)
    content = re.sub(r' =1490', r'&ito=1490', content)

    # Fix 5: Add proper line breaks before Drama Score section
    # Pattern: text runs into **Drama Score:** without break
    content = re.sub(r'(\w+[\.\!\?]) (\*\*Drama Score:\*\*)', r'\1\n\n\2', content)
    content = re.sub(r'(\]) (\*\*Drama Score:\*\*)', r'\1\n\n\2', content)

    # Fix 6: Ensure proper spacing around Drama Score section
    content = re.sub(r'(\*This post was automatically generated[^*]+\*)', r'\n\n\1', content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 ULTIMATE FIX: Making ALL posts perfect...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_all_post_issues(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 ULTIMATE FIXED {fixed_count} posts!")

if __name__ == "__main__":
    main()
