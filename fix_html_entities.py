#!/usr/bin/env python3
"""
Fix ALL HTML entities in existing Jekyll posts and JSON data
"""

import re
import html
import json
from pathlib import Path

def comprehensive_entity_fix(text):
    """Apply the same comprehensive entity fixing as the scraper"""
    if not text:
        return text

    # Decode standard HTML entities
    text = html.unescape(text)

    # Fix bracketed entities
    text = re.sub(r'\[&#8230;\]', '...', text)
    text = re.sub(r'\[&hellip;\]', '...', text)

    # Fix numeric entities
    text = re.sub(r'&#8230;', '...', text)
    text = re.sub(r'&#8217;', "'", text)
    text = re.sub(r'&#8216;', "'", text)
    text = re.sub(r'&#8220;', '"', text)
    text = re.sub(r'&#8221;', '"', text)
    text = re.sub(r'&#8211;', '–', text)
    text = re.sub(r'&#8212;', '—', text)
    text = re.sub(r'&#38;', '&', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'&#34;', '"', text)
    text = re.sub(r'&#60;', '<', text)
    text = re.sub(r'&#62;', '>', text)

    # Fix named entities
    text = re.sub(r'&hellip;', '...', text)
    text = re.sub(r'&rsquo;', "'", text)
    text = re.sub(r'&lsquo;', "'", text)
    text = re.sub(r'&rdquo;', '"', text)
    text = re.sub(r'&ldquo;', '"', text)
    text = re.sub(r'&ndash;', '–', text)
    text = re.sub(r'&mdash;', '—', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&apos;', "'", text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)

    # Clean up any remaining malformed entities
    text = re.sub(r'&[a-zA-Z0-9#]+;?', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def fix_markdown_posts():
    """Fix HTML entities in Jekyll posts"""
    posts_dir = Path('_posts')
    fixed_count = 0

    for post_file in posts_dir.glob('*.md'):
        with open(post_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixed_content = comprehensive_entity_fix(content)

        if fixed_content != original_content:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {post_file.name}")
            fixed_count += 1

    return fixed_count

def fix_json_data():
    """Fix HTML entities in JSON data files"""
    json_files = ['data/gossip_data.json']
    fixed_count = 0

    for json_file in json_files:
        json_path = Path(json_file)
        if not json_path.exists():
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Fix entities in the JSON data recursively
        def fix_json_recursive(obj):
            if isinstance(obj, dict):
                return {k: fix_json_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [fix_json_recursive(item) for item in obj]
            elif isinstance(obj, str):
                return comprehensive_entity_fix(obj)
            else:
                return obj

        fixed_data = fix_json_recursive(data)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Fixed JSON: {json_file}")
        fixed_count += 1

    return fixed_count

if __name__ == "__main__":
    print("🧹 Starting comprehensive HTML entity cleanup...")

    md_fixed = fix_markdown_posts()
    json_fixed = fix_json_data()

    print(f"\n🎯 Cleanup complete!")
    print(f"   📝 Fixed {md_fixed} markdown posts")
    print(f"   📊 Fixed {json_fixed} JSON files")
    print(f"   ✨ Your gossip empire is now entity-free!")
