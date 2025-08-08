#!/usr/bin/env python3
"""
Emergency YAML Fix - Fix Jekyll front matter syntax
"""

import re
from pathlib import Path

def clean_yaml_list(match_text):
    """Clean YAML list items by removing quotes"""
    items = [item.strip().strip('"\'') for item in match_text.split(',')]
    return f"tags: [{', '.join(items)}]"

def clean_yaml_dict(match_text):
    """Clean YAML dictionary by removing quotes"""
    cleaned = match_text.replace('"', '').replace("'", '')
    return f"mentions: {{{cleaned}}}"

def fix_yaml_syntax(content):
    """Fix YAML syntax issues in front matter only"""
    if not content.startswith('---\n'):
        return content

    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return content

    front_matter = parts[1]
    post_content = parts[2]

    original_fm = front_matter

    # Fix tags: remove quotes around individual items
    front_matter = re.sub(
        r"tags: \[([^\]]+)\]",
        lambda m: clean_yaml_list(m.group(1)),
        front_matter
    )

    # Fix mentions: remove quotes from keys/values
    front_matter = re.sub(
        r"mentions: \{([^}]+)\}",
        lambda m: clean_yaml_dict(m.group(1)),
        front_matter
    )

    # Fix double quotes in titles
    front_matter = re.sub(r'title: "([^"]*)"([^"]*)"', r'title: "\1\2"', front_matter)

    if front_matter != original_fm:
        return f"---\n{front_matter}---\n{post_content}"

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing YAML syntax in Jekyll posts...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_yaml_syntax(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed YAML syntax in {fixed_count} posts!")

    # Create summary
    with open('yaml_fix_summary.txt', 'w') as f:
        f.write(f"YAML Fix Summary\n")
        f.write(f"================\n")
        f.write(f"Files fixed: {fixed_count}\n")
        f.write(f"Backup branch created\n")

if __name__ == "__main__":
    main()
