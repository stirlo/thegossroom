#!/usr/bin/env python3
"""
Fix all YAML issues in Jekyll posts
"""

import re
from pathlib import Path

def fix_yaml_comprehensive(content):
    """Fix all YAML syntax issues"""
    if not content.startswith('---\n'):
        return content

    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return content

    front_matter = parts[1]
    post_content = parts[2]
    original_fm = front_matter

    # Fix 1: Remove quotes from tags array items
    def fix_tags(match):
        tag_list = match.group(1)
        # Remove all quotes from individual items
        clean_tags = re.sub(r"['\"]([^'\"]+)['\"]", r'\1', tag_list)
        return f"tags: [{clean_tags}]"

    front_matter = re.sub(r"tags: \[([^\]]+)\]", fix_tags, front_matter)

    # Fix 2: Remove quotes from mentions dictionary
    def fix_mentions(match):
        mentions_content = match.group(1)
        clean_mentions = mentions_content.replace('"', '').replace("'", '')
        return f"mentions: {{{clean_mentions}}}"

    front_matter = re.sub(r"mentions: \{([^}]+)\}", fix_mentions, front_matter)

    # Fix 3: Fix broken URLs with spaces
    def fix_url_spaces(match):
        url = match.group(1)
        # Replace spaces in URL parameters with %20
        if '?' in url:
            base, params = url.split('?', 1)
            params = params.replace(' =', '&').replace(' _', '&')
            url = f"{base}?{params}"
        return f'source_url: "{url}"'

    front_matter = re.sub(r'source_url: "([^"]+)"', fix_url_spaces, front_matter)

    if front_matter != original_fm:
        return f"---\n{front_matter}---\n{post_content}"

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Comprehensive YAML fix...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_yaml_comprehensive(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
