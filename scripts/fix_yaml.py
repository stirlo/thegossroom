#!/usr/bin/env python3
"""
Fix double quotes in mentions keys
"""

import re
from pathlib import Path

def fix_double_quotes_in_mentions(content):
    """Fix double quotes in mentions field keys"""

    # Pattern: mentions: {'key': value, ''key': value}
    # Fix the double quotes at start of keys
    def fix_mentions_field(match):
        mentions_content = match.group(1)
        # Fix double quotes: ''key' -> 'key'
        fixed_content = re.sub(r"''([^']+)'", r"'\1'", mentions_content)
        return f"mentions: {{{fixed_content}}}"

    content = re.sub(r'mentions: \{([^}]+)\}', fix_mentions_field, content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing double quotes in mentions...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_double_quotes_in_mentions(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
