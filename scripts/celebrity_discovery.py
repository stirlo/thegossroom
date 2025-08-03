#!/usr/bin/env python3
"""
Celebrity Auto-Discovery System
Automatically finds and adds new celebrities based on mention frequency and drama scores
"""

import yaml
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import re

class CelebrityDiscovery:
    def __init__(self):
        self.base_path = Path.cwd()
        self.discovery_threshold = 50  # Minimum drama score for auto-discovery
        self.mention_threshold = 3     # Minimum mentions in posts
        self.time_window = 30          # Days to look back for discovery

    def discover_new_celebrities(self):
        """Auto-discover new celebrities from recent posts"""
        print("🔍 Scanning for new celebrity mentions...")

        # Load existing celebrities
        celebrities_file = self.base_path / '_data' / 'celebrities.yml'
        existing_celebrities = set()

        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                existing_data = yaml.safe_load(f) or {}
                existing_celebrities = set(existing_data.keys())

        # Load tag management whitelist
        tag_mgmt_file = self.base_path / '_data' / 'tag_management.yml'
        whitelist = set()

        if tag_mgmt_file.exists():
            with open(tag_mgmt_file, 'r') as f:
                tag_data = yaml.safe_load(f) or {}
                whitelist = set(tag_data.get('celebrity_whitelist', []))

        # Scan recent posts for potential celebrities
        potential_celebrities = self.scan_recent_posts()

        # Filter and score potential celebrities
        new_discoveries = []
        cutoff_date = datetime.now() - timedelta(days=self.time_window)

        for name, data in potential_celebrities.items():
            # Skip if already exists
            if name in existing_celebrities:
                continue

            # Check if in whitelist (auto-approve)
            if name in whitelist:
                total_score = sum(data['scores'])
                if total_score >= self.discovery_threshold:
                    new_discoveries.append({
                        'name': name,
                        'drama_score': total_score,
                        'mention_count': len(data['scores']),
                        'first_mentioned': min(data['dates']).strftime('%Y-%m-%d'),
                        'status': 'new',
                        'source': 'whitelist',
                        'tags': list(set(data['tags']))[:5]  # Top 5 unique tags
                    })
                    continue

            # Check discovery criteria for unknown celebrities
            total_score = sum(data['scores'])
            mention_count = len(data['scores'])

            if (total_score >= self.discovery_threshold and 
                mention_count >= self.mention_threshold):

                new_discoveries.append({
                    'name': name,
                    'drama_score': total_score,
                    'mention_count': mention_count,
                    'first_mentioned': min(data['dates']).strftime('%Y-%m-%d'),
                    'status': 'new',
                    'source': 'auto-discovery',
                    'tags': list(set(data['tags']))[:5]
                })

        # Add new discoveries to celebrities.yml
        if new_discoveries:
            self.add_new_celebrities(new_discoveries)
            print(f"✅ Discovered {len(new_discoveries)} new celebrities!")

            for celeb in new_discoveries:
                print(f"   🌟 {celeb['name']} (Score: {celeb['drama_score']}, Mentions: {celeb['mention_count']})")
        else:
            print("📭 No new celebrities discovered")

    def scan_recent_posts(self):
        """Scan recent posts for celebrity mentions"""
        posts_dir = self.base_path / '_posts'
        if not posts_dir.exists():
            return {}

        potential_celebrities = defaultdict(lambda: {'scores': [], 'dates': [], 'tags': []})
        cutoff_date = datetime.now() - timedelta(days=self.time_window)

        for post_file in posts_dir.glob('*.md'):
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.startswith('---'):
                    continue

                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue

                front_matter = yaml.safe_load(parts[1])
                post_date = datetime.strptime(str(front_matter.get('date', '1970-01-01'))[:10], '%Y-%m-%d')

                if post_date < cutoff_date:
                    continue

                drama_score = front_matter.get('drama_score', 0)
                tags = front_matter.get('tags', [])
                primary_celebrity = front_matter.get('primary_celebrity', '')

                # Extract potential celebrity names from tags and content
                celebrity_candidates = set()

                # From primary_celebrity field
                if primary_celebrity:
                    celebrity_candidates.add(self.normalize_name(primary_celebrity))

                # From tags (look for person-like tags)
                for tag in tags:
                    normalized = self.normalize_name(tag)
                    if self.looks_like_person_name(normalized):
                        celebrity_candidates.add(normalized)

                # From title and content (basic name extraction)
                title = front_matter.get('title', '')
                content_text = parts[2]

                for name in self.extract_names_from_text(title + ' ' + content_text):
                    celebrity_candidates.add(self.normalize_name(name))

                # Record data for each candidate
                for candidate in celebrity_candidates:
                    if candidate and len(candidate) > 2:  # Skip very short names
                        potential_celebrities[candidate]['scores'].append(drama_score)
                        potential_celebrities[candidate]['dates'].append(post_date)
                        potential_celebrities[candidate]['tags'].extend(tags)

            except Exception as e:
                continue

        return dict(potential_celebrities)

    def normalize_name(self, name):
        """Normalize celebrity name for consistency"""
        if not name:
            return ''

        # Convert to lowercase, replace spaces/hyphens with underscores
        normalized = re.sub(r'[^\w\s-]', '', str(name).lower())
        normalized = re.sub(r'[\s-]+', '_', normalized)
        normalized = normalized.strip('_')

        return normalized

    def looks_like_person_name(self, name):
        """Check if a tag looks like a person's name"""
        if not name or len(name) < 3:
            return False

        # Skip obvious non-person tags
        skip_patterns = [
            r'^(the|and|or|in|on|at|to|for|with|by)_',
            r'_(news|update|drama|gossip|story|post|article)$',
            r'^(breaking|latest|new|hot|trending)_',
            r'_(brand|company|show|movie|song|album)$'
        ]

        for pattern in skip_patterns:
            if re.search(pattern, name):
                return False

        # Look for person-like patterns
        person_patterns = [
            r'^[a-z]+_[a-z]+$',  # first_last
            r'^[a-z]+_[a-z]+_[a-z]+$',  # first_middle_last
        ]

        for pattern in person_patterns:
            if re.match(pattern, name):
                return True

        return False

    def extract_names_from_text(self, text):
        """Extract potential celebrity names from text"""
        # Simple name extraction - look for capitalized words
        names = []

        # Find patterns like "FirstName LastName"
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(name_pattern, text)

        for match in matches:
            # Skip common non-name phrases
            if not any(word in match.lower() for word in ['the', 'and', 'new', 'latest', 'breaking']):
                names.append(match)

        return names

    def add_new_celebrities(self, new_discoveries):
        """Add new celebrities to the celebrities.yml file"""
        celebrities_file = self.base_path / '_data' / 'celebrities.yml'

        # Load existing data
        existing_data = {}
        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                existing_data = yaml.safe_load(f) or {}

        # Add new discoveries
        for celeb in new_discoveries:
            existing_data[celeb['name']] = {
                'drama_score': celeb['drama_score'],
                'status': celeb['status'],
                'first_mentioned': celeb['first_mentioned'],
                'discovery_source': celeb['source'],
                'tags': celeb['tags']
            }

        # Save updated data
        with open(celebrities_file, 'w') as f:
            yaml.dump(existing_data, f, default_flow_style=False, sort_keys=True)

    def promote_new_celebrities(self):
        """Promote 'new' celebrities to regular status after 30 days"""
        celebrities_file = self.base_path / '_data' / 'celebrities.yml'

        if not celebrities_file.exists():
            return

        with open(celebrities_file, 'r') as f:
            celebrities = yaml.safe_load(f) or {}

        updated_count = 0
        promotion_cutoff = datetime.now() - timedelta(days=30)

        for name, info in celebrities.items():
            if info.get('status') == 'new':
                first_mentioned = info.get('first_mentioned')
                if first_mentioned:
                    try:
                        mention_date = datetime.strptime(first_mentioned, '%Y-%m-%d')
                        if mention_date < promotion_cutoff:
                            info['status'] = 'active'
                            updated_count += 1
                            print(f"⭐ Promoted {name} from new to active status")
                    except ValueError:
                        pass

        if updated_count > 0:
            with open(celebrities_file, 'w') as f:
                yaml.dump(celebrities, f, default_flow_style=False, sort_keys=True)
            print(f"✅ Promoted {updated_count} celebrities to active status")
        else:
            print("📭 No celebrities ready for promotion")

if __name__ == "__main__":
    import sys

    discovery = CelebrityDiscovery()

    if len(sys.argv) > 1:
        if sys.argv[1] == "discover":
            discovery.discover_new_celebrities()
        elif sys.argv[1] == "promote":
            discovery.promote_new_celebrities()
        else:
            print("Usage: python celebrity_discovery.py [discover|promote]")
    else:
        discovery.discover_new_celebrities()
