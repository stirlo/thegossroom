#!/usr/bin/env python3
"""
MEGA FIX: Restore tag quotes AND fix YAML parsing errors
"""

import re
from pathlib import Path

def mega_fix_yaml(content):
    """Fix ALL YAML issues in one go"""

    # Fix 1: Restore quotes to tags
    def fix_tags_line(match):
        tags_content = match.group(1)
        items = [item.strip() for item in tags_content.split(',')]
        quoted_items = [f"'{item}'" if not (item.startswith("'") or item.startswith('"')) else item for item in items]
        return f"tags: [{', '.join(quoted_items)}]"

    content = re.sub(r'tags: \[([^\]]+)\]', fix_tags_line, content)

    # Fix 2: Missing closing quotes in source_url
    content = re.sub(r'source_url: "([^"]*)\n', r'source_url: "\1"\n', content)
    content = re.sub(r'source_url: "([^"]*)"([^"\n]*)\n', r'source_url: "\1\2"\n', content)

    # Fix 3: Broken mentions mapping - add quotes around keys
    def fix_mentions(match):
        mentions_content = match.group(1)
        # Add quotes around unquoted keys
        fixed = re.sub(r'(\w+):', r"'\1':", mentions_content)
        return f"mentions: {{{fixed}}}"

    content = re.sub(r'mentions: \{([^}]+)\}', fix_mentions, content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 MEGA FIX: Restoring tag quotes AND fixing YAML errors...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = mega_fix_yaml(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 MEGA FIXED {fixed_count} posts!")

if __name__ == "__main__":
    main()
