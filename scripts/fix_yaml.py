#!/usr/bin/env python3
"""
EMERGENCY FIX: Fix broken mentions YAML syntax
"""

import re
from pathlib import Path

def fix_mentions_syntax(content):
    """Fix the mentions field syntax specifically"""

    # Pattern 1: mentions: {key: value} -> mentions: {'key': value}
    def fix_mentions_mapping(match):
        mentions_content = match.group(1)
        # Split by comma and fix each key-value pair
        pairs = []
        for pair in mentions_content.split(','):
            pair = pair.strip()
            if ':' in pair:
                key, value = pair.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Add quotes around key if not already quoted
                if not (key.startswith("'") or key.startswith('"')):
                    key = f"'{key}'"
                pairs.append(f"{key}: {value}")

        return f"mentions: {{{', '.join(pairs)}}}"

    # Apply the fix
    content = re.sub(r'mentions: \{([^}]+)\}', fix_mentions_mapping, content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🚨 EMERGENCY: Fixing mentions syntax...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_mentions_syntax(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 EMERGENCY FIXED {fixed_count} posts!")

if __name__ == "__main__":
    main()
