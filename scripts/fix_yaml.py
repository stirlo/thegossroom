#!/usr/bin/env python3
"""
RESTORE quotes to YAML tags - they were needed after all!
"""

from pathlib import Path
import re

def restore_quotes_to_tags(content):
    """Add quotes back to unquoted tags"""

    # Find tags without quotes and add them back
    def fix_tags_line(match):
        tags_content = match.group(1)
        # Split by comma, strip whitespace, add quotes
        items = [item.strip() for item in tags_content.split(',')]
        quoted_items = [f"'{item}'" if not (item.startswith("'") or item.startswith('"')) else item for item in items]
        return f"tags: [{', '.join(quoted_items)}]"

    # Pattern: tags: [unquoted, items, here]
    content = re.sub(r'tags: \[([^\]]+)\]', fix_tags_line, content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Restoring quotes to YAML tags...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = restore_quotes_to_tags(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Restored quotes to {fixed_count} posts!")

if __name__ == "__main__":
    main()
