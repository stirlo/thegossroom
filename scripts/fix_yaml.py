#!/usr/bin/env python3
"""
Fix missing front matter closing tags
"""

import re
from pathlib import Path

def fix_front_matter_closing(content):
    """Fix missing --- closing tags in front matter"""

    # Pattern: finds YAML that ends abruptly without proper closing
    # Look for } followed by --- and content (missing newline and proper closing)
    pattern = r'(mentions: \{[^}]+\}) --- ([^-])'

    if re.search(pattern, content):
        # Replace with proper closing
        content = re.sub(pattern, r'\1\n---\n\n\2', content)
        return content

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing front matter closing tags...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_front_matter_closing(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
