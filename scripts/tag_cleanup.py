#!/usr/bin/env python3
"""
Advanced Tag Cleanup System
Automatically cleans, merges, and manages tags across all posts
"""

import yaml
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import argparse

class TagCleanup:
    def __init__(self):
        self.base_path = Path.cwd()
        self.posts_dir = self.base_path / '_posts'
        self.data_dir = self.base_path / '_data'

        self.load_tag_management()
        self.load_celebrities()

    def load_tag_management(self):
        """Load tag management configuration"""
        tag_file = self.data_dir / 'tag_management.yml'
        if tag_file.exists():
            with open(tag_file, 'r') as f:
                self.tag_config = yaml.safe_load(f) or {}
        else:
            self.tag_config = {'whitelist': [], 'blacklist': [], 'replacements': {}}

    def load_celebrities(self):
        """Load celebrity data for validation"""
        celebrities_file = self.data_dir / 'celebrities.yml'
        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                self.celebrities = yaml.safe_load(f) or {}
        else:
            self.celebrities = {}

    def cleanup_tags(self):
        """Main tag cleanup function"""
        print("🧹 Starting comprehensive tag cleanup...")

        self.remove_blacklisted_tags()
        self.merge_similar_tags()
        self.fix_tag_formatting()
        self.remove_orphaned_tags()
        self.validate_celebrity_tags()

        print("✅ Tag cleanup completed!")

    def remove_blacklisted_tags(self):
        """Remove blacklisted tags from all posts"""
        blacklist = self.tag_config.get('blacklist', [])
        if not blacklist:
            return

        print(f"🚫 Removing {len(blacklist)} blacklisted tags...")

        removed_count = 0
        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2]

                        original_tags = front_matter.get('tags', [])
                        cleaned_tags = [tag for tag in original_tags if tag not in blacklist]

                        if len(cleaned_tags) != len(original_tags):
                            front_matter['tags'] = cleaned_tags

                            # Rebuild file
                            new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                            with open(post_file, 'w') as f:
                                f.write(new_content)

                            removed_count += 1

            except Exception as e:
                print(f"❌ Error processing {post_file}: {e}")

        if removed_count > 0:
            print(f"🧹 Cleaned blacklisted tags from {removed_count} posts")

    def merge_similar_tags(self):
        """Merge similar tags based on replacement rules"""
        replacements = self.tag_config.get('replacements', {})
        if not replacements:
            return

        print(f"🔄 Merging {len(replacements)} tag replacements...")

        merged_count = 0
        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2]

                        tags = front_matter.get('tags', [])
                        updated_tags = []

                        for tag in tags:
                            # Check if tag should be replaced
                            replacement = replacements.get(tag, tag)
                            updated_tags.append(replacement)

                        # Remove duplicates while preserving order
                        final_tags = []
                        seen = set()
                        for tag in updated_tags:
                            if tag not in seen:
                                final_tags.append(tag)
                                seen.add(tag)

                        if final_tags != tags:
                            front_matter['tags'] = final_tags

                            # Rebuild file
                            new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                            with open(post_file, 'w') as f:
                                f.write(new_content)

                            merged_count += 1

            except Exception as e:
                print(f"❌ Error processing {post_file}: {e}")

        if merged_count > 0:
            print(f"🔄 Merged tags in {merged_count} posts")

    def fix_tag_formatting(self):
        """Fix common tag formatting issues"""
        print("🔧 Fixing tag formatting issues...")

        fixed_count = 0
        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2]

                        tags = front_matter.get('tags', [])
                        cleaned_tags = []

                        for tag in tags:
                            # Clean tag formatting
                            clean_tag = self.clean_tag_format(str(tag))
                            if clean_tag and len(clean_tag) > 1:  # Skip empty or single char tags
                                cleaned_tags.append(clean_tag)

                        # Remove duplicates
                        final_tags = list(dict.fromkeys(cleaned_tags))

                        if final_tags != tags:
                            front_matter['tags'] = final_tags

                            # Rebuild file
                            new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                            with open(post_file, 'w') as f:
                                f.write(new_content)

                            fixed_count += 1

            except Exception as e:
                print(f"❌ Error processing {post_file}: {e}")

        if fixed_count > 0:
            print(f"🔧 Fixed formatting in {fixed_count} posts")

    def clean_tag_format(self, tag):
        """Clean individual tag formatting"""
        # Convert to lowercase
        clean_tag = tag.lower().strip()

        # Remove special characters except hyphens and underscores
        clean_tag = re.sub(r'[^a-z0-9\-_\s]', '', clean_tag)

        # Replace spaces with underscores
        clean_tag = re.sub(r'\s+', '_', clean_tag)

        # Remove multiple consecutive underscores/hyphens
        clean_tag = re.sub(r'[_\-]+', '_', clean_tag)

        # Remove leading/trailing underscores
        clean_tag = clean_tag.strip('_-')

        return clean_tag

    def remove_orphaned_tags(self):
        """Remove tags that appear in very few posts"""
        print("🗑️ Removing orphaned tags...")

        # Count tag usage
        tag_counts = Counter()
        all_posts = list(self.posts_dir.glob('*.md'))

        for post_file in all_posts:
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        tags = front_matter.get('tags', [])

                        for tag in tags:
                            tag_counts[tag] += 1

            except Exception as e:
                continue

        # Find orphaned tags (used in only 1 post and not whitelisted)
        whitelist = set(self.tag_config.get('whitelist', []))
        celebrity_names = set(self.celebrities.keys())

        orphaned_tags = set()
        for tag, count in tag_counts.items():
            if (count == 1 and 
                tag not in whitelist and 
                tag not in celebrity_names and
                len(tag) < 15):  # Don't remove long descriptive tags
                orphaned_tags.add(tag)

        if not orphaned_tags:
            print("📊 No orphaned tags found")
            return

        print(f"🗑️ Removing {len(orphaned_tags)} orphaned tags...")

        # Remove orphaned tags
        cleaned_count = 0
        for post_file in all_posts:
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2]

                        original_tags = front_matter.get('tags', [])
                        cleaned_tags = [tag for tag in original_tags if tag not in orphaned_tags]

                        if len(cleaned_tags) != len(original_tags):
                            front_matter['tags'] = cleaned_tags

                            # Rebuild file
                            new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                            with open(post_file, 'w') as f:
                                f.write(new_content)

                            cleaned_count += 1

            except Exception as e:
                continue

        if cleaned_count > 0:
            print(f"🗑️ Removed orphaned tags from {cleaned_count} posts")

    def validate_celebrity_tags(self):
        """Ensure celebrity tags match known celebrities"""
        print("⭐ Validating celebrity tags...")

        celebrity_names = set(self.celebrities.keys())
        validated_count = 0

        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2]

                        tags = front_matter.get('tags', [])
                        primary_celebrity = front_matter.get('primary_celebrity')

                        # Validate primary celebrity
                        if primary_celebrity and primary_celebrity not in celebrity_names:
                            # Try to find a match in tags
                            for tag in tags:
                                if tag in celebrity_names:
                                    front_matter['primary_celebrity'] = tag
                                    validated_count += 1
                                    break
                            else:
                                # Remove invalid primary celebrity
                                if 'primary_celebrity' in front_matter:
                                    del front_matter['primary_celebrity']
                                    validated_count += 1

                        # Update file if changed
                        if validated_count > 0:
                            new_content = f"---\n{yaml.dump(front_matter, default_flow_style=False)}---{post_content}"
                            with open(post_file, 'w') as f:
                                f.write(new_content)

            except Exception as e:
                continue

        if validated_count > 0:
            print(f"⭐ Validated {validated_count} celebrity references")
        else:
            print("📊 All celebrity tags validated")

    def deep_clean(self):
        """Perform deep cleaning including advanced analysis"""
        print("🔍 Starting deep tag analysis and cleanup...")

        self.cleanup_tags()
        self.analyze_tag_relationships()
        self.suggest_tag_improvements()

        print("✅ Deep cleanup completed!")

    def analyze_tag_relationships(self):
        """Analyze which tags frequently appear together"""
        print("📊 Analyzing tag relationships...")

        # This could be expanded to suggest tag mergers or improvements
        # For now, just report on tag usage patterns

        tag_pairs = Counter()
        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        tags = front_matter.get('tags', [])

                        # Count tag pairs
                        for i, tag1 in enumerate(tags):
                            for tag2 in tags[i+1:]:
                                pair = tuple(sorted([tag1, tag2]))
                                tag_pairs[pair] += 1

            except Exception as e:
                continue

        # Report top tag pairs
        top_pairs = tag_pairs.most_common(10)
        if top_pairs:
            print("🔗 Top tag combinations:")
            for (tag1, tag2), count in top_pairs:
                print(f"   {tag1} + {tag2}: {count} posts")

    def suggest_tag_improvements(self):
        """Suggest tag improvements based on analysis"""
        print("💡 Analyzing for tag improvement suggestions...")

        # This could be expanded with ML-based suggestions
        # For now, just basic pattern recognition

        suggestions = []

        # Find tags that might be duplicates
        all_tags = set()
        for post_file in self.posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        tags = front_matter.get('tags', [])
                        all_tags.update(tags)

            except Exception as e:
                continue

        # Look for similar tags
        tag_list = list(all_tags)
        for i, tag1 in enumerate(tag_list):
            for tag2 in tag_list[i+1:]:
                if self.tags_are_similar(tag1, tag2):
                    suggestions.append(f"Consider merging '{tag1}' and '{tag2}'")

        if suggestions:
            print("💡 Tag improvement suggestions:")
            for suggestion in suggestions[:5]:  # Top 5 suggestions
                print(f"   {suggestion}")
        else:
            print("📊 No obvious tag improvements needed")

    def tags_are_similar(self, tag1, tag2):
        """Check if two tags are similar enough to merge"""
        # Simple similarity check
        if abs(len(tag1) - len(tag2)) > 3:
            return False

        # Check for common patterns
        if tag1.replace('_', '') == tag2.replace('_', ''):
            return True

        if tag1.replace('-', '') == tag2.replace('-', ''):
            return True

        # Check for plural/singular
        if tag1.endswith('s') and tag1[:-1] == tag2:
            return True
        if tag2.endswith('s') and tag2[:-1] == tag1:
            return True

        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tag Cleanup System')
    parser.add_argument('action', choices=['cleanup', 'deep-clean'], 
                       help='Action to perform')

    args = parser.parse_args()

    cleanup = TagCleanup()

    if args.action == 'cleanup':
        cleanup.cleanup_tags()
    elif args.action == 'deep-clean':
        cleanup.deep_clean()
