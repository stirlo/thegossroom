#!/usr/bin/env python3
"""
Fix the ACTUAL formatting issues causing Jekyll errors
"""

import re
from pathlib import Path

def fix_real_issues(content):
    """Fix the actual problems we can see"""

    # Fix 1: Ensure proper blank line after front matter
    # Pattern: ---\n"content or ---\nContent
    content = re.sub(r'---\n"', r'---\n\n"', content)
    content = re.sub(r'---\n([A-Z])', r'---\n\n\1', content)
    content = re.sub(r'---\n([a-z])', r'---\n\n\1', content)

    # Fix 2: Fix malformed ending with space after ---
    content = re.sub(r'--- \n', r'---\n', content)
    content = re.sub(r'--- $', r'---', content, flags=re.MULTILINE)

    # Fix 3: Add proper line breaks before Drama Score
    content = re.sub(r'(\w) (\*\*Drama Score:\*\*)', r'\1\n\n\2', content)

    # Fix 4: Ensure final --- is on its own line
    content = re.sub(r'(\)) (---)', r'\1\n\n\2', content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing REAL formatting issues...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_real_issues(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
