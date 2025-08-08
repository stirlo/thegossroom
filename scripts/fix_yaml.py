#!/usr/bin/env python3
"""
Fix Jekyll post formatting issues
"""

import re
from pathlib import Path

def fix_post_formatting(content):
    """Fix various Jekyll post issues"""

    # Fix 1: Add line breaks to front matter if it's all on one line
    if content.count('\n') < 10 and '---' in content:
        # Replace spaces between YAML fields with newlines
        content = re.sub(r' (layout|title|date|categories|tags|drama_score|primary_celebrity|source|source_url|mentions):', r'\n\1:', content)

    # Fix 2: Fix missing closing quotes in titles
    content = re.sub(r'title: "([^"]*)"([^"\n]*)\n', r'title: "\1\2"\n', content)
    content = re.sub(r'title: "([^"]*)\n', r'title: "\1"\n', content)

    # Fix 3: Ensure proper YAML structure
    lines = content.split('\n')
    if lines and lines[0] == '---':
        # Find end of front matter
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx > 0:
            # Rebuild front matter with proper formatting
            front_matter = []
            for line in lines[1:end_idx]:
                if line.strip():
                    front_matter.append(line)

            # Reconstruct with proper spacing
            new_content = ['---']
            new_content.extend(front_matter)
            new_content.append('---')
            new_content.append('')  # Empty line after front matter
            new_content.extend(lines[end_idx+1:])

            content = '\n'.join(new_content)

    return content

def main():
    posts_dir = Path('_posts')
    fixed_count = 0

    print("🔧 Fixing Jekyll post formatting...")

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_post_formatting(original_content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    print(f"\n🎯 Fixed {fixed_count} posts!")

if __name__ == "__main__":
    main()
