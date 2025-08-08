#!/usr/bin/env python3
"""
Fix all YAML issues in Jekyll posts - WITH DEBUGGING
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

    print(f"    Original tags line: {[line for line in front_matter.split('\\n') if 'tags:' in line]}")

    # Fix 1: Remove quotes from tags array items
    def fix_tags(match):
        tag_list = match.group(1)
        print(f"    Found tags to fix: {tag_list}")
        # Remove all quotes from individual items
        clean_tags = re.sub(r"['\"]([^'\"]+)['\"]", r'\\1', tag_list)
        return f"tags: [{clean_tags}]"

    front_matter = re.sub(r"tags: \\[([^\\]]+)\\]", fix_tags, front_matter)

    # Fix 2: Remove quotes from mentions dictionary
    def fix_mentions(match):
        mentions_content = match.group(1)
        print(f"    Found mentions to fix: {mentions_content}")
        clean_mentions = mentions_content.replace('"', '').replace("'", '')
        return f"mentions: {{{clean_mentions}}}"

    front_matter = re.sub(r"mentions: \\{([^}]+)\\}", fix_mentions, front_matter)

    # Fix 3: Fix broken URLs with spaces
    def fix_url_spaces(match):
        url = match.group(1)
        print(f"    Found URL to fix: {url[:50]}...")
        if '?' in url and ' =' in url:
            base, params = url.split('?', 1)
            params = params.replace(' =', '&').replace(' _', '&')
            url = f"{base}?{params}"
            print(f"    Fixed URL to: {url[:50]}...")
        return f'source_url: "{url}"'

    front_matter = re.sub(r'source_url: "([^"]+)"', fix_url_spaces, front_matter)

    if front_matter != original_fm:
        print(f"    ✅ Changes made!")
        return f"---\\n{front_matter}---\\n{post_content}"
    else:
        print(f"    ❌ No changes needed")

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print(f"🔧 Looking for posts in: {posts_dir.absolute()}")
    print(f"🔧 Posts found: {len(list(posts_dir.glob('*.md')))}")

    for post_file in posts_dir.glob('*.md'):
        print(f"\\n📄 Processing: {post_file.name}")

        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_yaml_comprehensive(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()