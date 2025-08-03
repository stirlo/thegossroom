#!/usr/bin/env python3
"""
Memorial Cleanup System
Automatically manages memorial status and 18-month removal
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
import argparse

class MemorialCleanup:
    def __init__(self):
        self.base_path = Path.cwd()
        self.data_dir = self.base_path / '_data'
        self.load_celebrities()

    def load_celebrities(self):
        """Load celebrity data"""
        celebrities_file = self.data_dir / 'celebrities.yml'
        if celebrities_file.exists():
            with open(celebrities_file, 'r') as f:
                self.celebrities = yaml.safe_load(f) or {}
        else:
            self.celebrities = {}

    def cleanup_expired_memorials(self):
        """Remove celebrities who have been in memorial for 18+ months"""
        print("🕊️ Checking for expired memorial entries...")

        current_date = datetime.now()
        removed_count = 0
        updated_celebrities = {}

        for name, info in self.celebrities.items():
            should_remove = False

            # Check if memorial status has expired
            if info.get('status') == 'memorial':
                death_date = info.get('death_date')
                if death_date:
                    try:
                        death_datetime = datetime.strptime(death_date, '%Y-%m-%d')
                        expiry_date = death_datetime + timedelta(days=548)  # 18 months

                        if current_date >= expiry_date:
                            should_remove = True
                            print(f"🕊️ Removing expired memorial: {name} (died {death_date})")
                            removed_count += 1
                    except ValueError:
                        print(f"❌ Invalid death date format for {name}: {death_date}")

            # Keep if not expired
            if not should_remove:
                updated_celebrities[name] = info

        # Update celebrities data
        self.celebrities = updated_celebrities

        if removed_count > 0:
            self.save_celebrities()
            print(f"✅ Removed {removed_count} expired memorial entries")
        else:
            print("📊 No expired memorials found")

    def auto_memorialize_deceased(self):
        """Automatically detect and memorialize deceased celebrities"""
        print("🔍 Checking for deceased celebrities to memorialize...")

        # Known recent deaths that should be memorialized
        known_deaths = {
            'liam_payne': {
                'death_date': '2024-10-16',
                'memorial_note': 'Former One Direction member, remembered for his music and struggles'
            },
            'matthew_perry': {
                'death_date': '2023-10-28', 
                'memorial_note': 'Beloved Friends star and mental health advocate'
            }
            # Add more as needed
        }

        memorialized_count = 0
        for name, death_info in known_deaths.items():
            if name in self.celebrities and self.celebrities[name].get('status') != 'memorial':
                self.celebrities[name]['status'] = 'memorial'
                self.celebrities[name]['death_date'] = death_info['death_date']
                self.celebrities[name]['memorial_note'] = death_info['memorial_note']
                self.celebrities[name]['memorialized_date'] = datetime.now().strftime('%Y-%m-%d')

                print(f"🕊️ Memorialized: {name}")
                memorialized_count += 1

        if memorialized_count > 0:
            self.save_celebrities()
            print(f"✅ Memorialized {memorialized_count} celebrities")
        else:
            print("📊 No new memorializations needed")

    def update_memorial_expiry_dates(self):
        """Update memorial expiry dates for tracking"""
        print("📅 Updating memorial expiry dates...")

        updated_count = 0
        for name, info in self.celebrities.items():
            if (info.get('status') == 'memorial' and 
                info.get('death_date') and 
                not info.get('memorial_expires')):

                try:
                    death_date = datetime.strptime(info['death_date'], '%Y-%m-%d')
                    expiry_date = death_date + timedelta(days=548)  # 18 months
                    self.celebrities[name]['memorial_expires'] = expiry_date.strftime('%Y-%m-%d')
                    updated_count += 1
                except ValueError:
                    print(f"❌ Invalid death date for {name}: {info['death_date']}")

        if updated_count > 0:
            self.save_celebrities()
            print(f"✅ Updated {updated_count} memorial expiry dates")
        else:
            print("📊 All memorial expiry dates up to date")

    def save_celebrities(self):
        """Save updated celebrity data"""
        with open(self.data_dir / 'celebrities.yml', 'w') as f:
            f.write("# Celebrity Drama Tracking Database\n")
            f.write("# Auto-updated by discovery scripts and manual additions\n\n")
            yaml.dump(self.celebrities, f, default_flow_style=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Memorial Cleanup System')
    parser.add_argument('action', choices=['cleanup', 'memorialize', 'update-expiry'], 
                       help='Action to perform')

    args = parser.parse_args()

    memorial = MemorialCleanup()

    if args.action == 'cleanup':
        memorial.cleanup_expired_memorials()
    elif args.action == 'memorialize':
        memorial.auto_memorialize_deceased()
    elif args.action == 'update-expiry':
        memorial.update_memorial_expiry_dates()
