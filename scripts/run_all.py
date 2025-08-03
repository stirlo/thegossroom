#!/usr/bin/env python3
"""
Master Orchestration Script for Gossip Blog Automation
Runs all components in the correct order with error handling and logging
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import yaml
import json

class GossipBlogOrchestrator:
    def __init__(self):
        self.base_path = Path.cwd()
        self.scripts_dir = self.base_path / 'scripts'
        self.data_dir = self.base_path / '_data'
        self.posts_dir = self.base_path / '_posts'

        # Ensure directories exist
        self.scripts_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.posts_dir.mkdir(exist_ok=True)

        # Execution order and dependencies (UPDATED FOR EXISTING SCRIPTS)
        self.execution_order = [
            {
                'name': 'Tag Cleanup',
                'script': 'tag_cleanup.py',
                'description': 'Clean up and process tag management rules',
                'required': False,
                'frequency': 'daily'
            },
            {
                'name': 'Memorial Cleanup',
                'script': 'memorial_cleanup.py',
                'description': 'Clean up memorial celebrities after 18 months',
                'required': False,
                'frequency': 'weekly'
            },
            {
                'name': 'Enhanced Gossip Scraper',
                'script': 'enhanced_gossip_scraper.py',
                'description': 'Scrape RSS feeds and generate blog posts',
                'required': True,
                'frequency': 'hourly'
            },
            {
                'name': 'Celebrity Discovery',
                'script': 'celebrity_discovery.py',
                'description': 'Discover new celebrities from recent posts',
                'required': False,
                'frequency': 'daily'
            },
            {
                'name': 'Drama Temperature Calculator',
                'script': 'drama_temperature_calculator.py',
                'description': 'Calculate celebrity drama temperatures (legacy)',
                'required': False,
                'frequency': 'daily'
            },
            {
                'name': 'Temperature Calculator',
                'script': 'temperature_calculator.py',
                'description': 'Calculate celebrity drama temperatures (new)',
                'required': False,
                'frequency': 'daily'
            },
            {
                'name': 'Bluesky Poster',
                'script': 'bluesky_poster.py',
                'description': 'Post hottest gossip to Bluesky',
                'required': False,
                'frequency': 'hourly'
            }
        ]

        # Logging
        self.log_file = self.base_path / 'automation.log'

    def log(self, message, level='INFO'):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"

        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def check_dependencies(self):
        """Check if all required scripts exist"""
        missing_scripts = []
        available_scripts = []

        for step in self.execution_order:
            script_path = self.scripts_dir / step['script']
            if script_path.exists():
                available_scripts.append(step['script'])
            else:
                if step['required']:
                    missing_scripts.append(step['script'])
                else:
                    self.log(f"Optional script missing: {step['script']}", 'WARNING')

        self.log(f"Available scripts: {len(available_scripts)}")
        for script in available_scripts:
            self.log(f"  ✅ {script}")

        if missing_scripts:
            self.log(f"Missing required scripts: {missing_scripts}", 'ERROR')
            return False

        return True

    def run_script(self, script_name, description):
        """Run a single script with error handling"""
        script_path = self.scripts_dir / script_name

        if not script_path.exists():
            self.log(f"Script not found: {script_name}", 'WARNING')
            return False

        self.log(f"Starting: {description}")
        start_time = time.time()

        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for scraper
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                self.log(f"✅ Completed: {description} ({execution_time:.1f}s)")
                if result.stdout.strip():
                    # Show last few lines of output
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines[-3:]:  # Last 3 lines
                        if line.strip():
                            self.log(f"   {line.strip()}")
                return True
            else:
                self.log(f"❌ Failed: {description}", 'ERROR')
                if result.stderr.strip():
                    error_lines = result.stderr.strip().split('\n')
                    for line in error_lines[-3:]:  # Last 3 error lines
                        if line.strip():
                            self.log(f"   ERROR: {line.strip()}", 'ERROR')
                return False

        except subprocess.TimeoutExpired:
            self.log(f"⏰ Timeout: {description} (exceeded 10 minutes)", 'ERROR')
            return False
        except Exception as e:
            self.log(f"💥 Exception in {description}: {str(e)}", 'ERROR')
            return False

    def create_execution_summary(self, results):
        """Create execution summary"""
        total_steps = len(results)
        successful_steps = sum(1 for r in results if r['success'])
        failed_steps = total_steps - successful_steps

        summary = {
            'execution_time': datetime.now().isoformat(),
            'total_steps': total_steps,
            'successful_steps': successful_steps,
            'failed_steps': failed_steps,
            'success_rate': f"{(successful_steps/total_steps)*100:.1f}%",
            'results': results
        }

        # Save summary
        summary_file = self.data_dir / 'last_execution_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    def run_full_pipeline(self, force_all=False, frequency_filter=None):
        """Run the complete gossip blog automation pipeline"""
        self.log("🚀 Starting Gossip Blog Automation Pipeline")
        if frequency_filter:
            self.log(f"🎯 Running {frequency_filter} tasks only")
        self.log("=" * 60)

        # Check dependencies
        if not self.check_dependencies():
            self.log("❌ Dependency check failed. Continuing with available scripts.", 'WARNING')

        # Filter steps by frequency if specified
        steps_to_run = self.execution_order
        if frequency_filter:
            steps_to_run = [s for s in self.execution_order if s.get('frequency') == frequency_filter]
            self.log(f"Filtered to {len(steps_to_run)} {frequency_filter} tasks")

        # Track results
        results = []
        pipeline_start_time = time.time()

        # Execute each step
        for step in steps_to_run:
            step_result = {
                'name': step['name'],
                'script': step['script'],
                'required': step['required'],
                'frequency': step.get('frequency', 'unknown'),
                'success': False,
                'execution_time': 0
            }

            step_start = time.time()

            # Run the script
            success = self.run_script(step['script'], step['description'])

            step_result['success'] = success
            step_result['execution_time'] = time.time() - step_start
            results.append(step_result)

            # Handle failures
            if not success and step['required']:
                self.log(f"💀 Required step failed: {step['name']}", 'ERROR')
                if not force_all:
                    self.log("Aborting pipeline due to required step failure", 'ERROR')
                    break

            # Brief pause between steps
            time.sleep(2)

        # Calculate total execution time
        total_execution_time = time.time() - pipeline_start_time

        # Create summary
        summary = self.create_execution_summary(results)

        # Log final results
        self.log("=" * 60)
        self.log("🏁 Pipeline Execution Complete")
        self.log(f"⏱️  Total Time: {total_execution_time:.1f} seconds")
        self.log(f"✅ Success Rate: {summary['success_rate']}")
        self.log(f"📊 Steps: {summary['successful_steps']}/{summary['total_steps']} successful")

        # Show individual results
        for result in results:
            status = "✅" if result['success'] else "❌"
            required = " (REQUIRED)" if result['required'] else ""
            freq = f" [{result['frequency']}]"
            self.log(f"{status} {result['name']}{required}{freq}: {result['execution_time']:.1f}s")

        # Final status
        if summary['failed_steps'] == 0:
            self.log("🎉 All steps completed successfully!")
            return True
        else:
            required_failures = sum(1 for r in results if not r['success'] and r['required'])
            if required_failures > 0:
                self.log(f"💀 Pipeline failed: {required_failures} required steps failed", 'ERROR')
                return False
            else:
                self.log(f"⚠️  Pipeline completed with {summary['failed_steps']} optional failures", 'WARNING')
                return True

    def run_single_step(self, step_name):
        """Run a single step by name"""
        # Try exact name match first
        for step in self.execution_order:
            if step['name'].lower() == step_name.lower():
                self.log(f"🎯 Running single step: {step['name']}")
                success = self.run_script(step['script'], step['description'])

                if success:
                    self.log(f"✅ Single step completed: {step['name']}")
                else:
                    self.log(f"❌ Single step failed: {step['name']}", 'ERROR')

                return success

        # Try script name match
        for step in self.execution_order:
            if step['script'] == step_name or step['script'] == f"{step_name}.py":
                self.log(f"🎯 Running single step: {step['name']} ({step['script']})")
                success = self.run_script(step['script'], step['description'])

                if success:
                    self.log(f"✅ Single step completed: {step['name']}")
                else:
                    self.log(f"❌ Single step failed: {step['name']}", 'ERROR')

                return success

        # Try partial name match
        matches = []
        for step in self.execution_order:
            if step_name.lower() in step['name'].lower() or step_name.lower() in step['script'].lower():
                matches.append(step)

        if len(matches) == 1:
            step = matches[0]
            self.log(f"🎯 Running single step (partial match): {step['name']}")
            success = self.run_script(step['script'], step['description'])

            if success:
                self.log(f"✅ Single step completed: {step['name']}")
            else:
                self.log(f"❌ Single step failed: {step['name']}", 'ERROR')

            return success
        elif len(matches) > 1:
            self.log(f"❓ Multiple matches found for '{step_name}':", 'ERROR')
            for match in matches:
                self.log(f"   - {match['name']} ({match['script']})")
            return False

        self.log(f"❓ Step not found: {step_name}", 'ERROR')
        self.log("Available steps:")
        for step in self.execution_order:
            self.log(f"   - {step['name']} ({step['script']})")
        return False

    def show_status(self):
        """Show current system status"""
        self.log("📊 Gossip Blog Automation Status")
        self.log("=" * 40)

        # Check script availability
        self.log("📁 Script Availability:")
        for step in self.execution_order:
            script_path = self.scripts_dir / step['script']
            status = "✅" if script_path.exists() else "❌"
            required = " (REQUIRED)" if step['required'] else ""
            freq = f" [{step.get('frequency', 'unknown')}]"
            self.log(f"   {status} {step['script']}{required}{freq}")

        # Check data files
        self.log("\n📄 Data Files:")
        data_files = [
            'celebrities.yml',
            'tag_management.yml', 
            'rss_sources.yml',
            'last_execution_summary.json'
        ]

        for file_name in data_files:
            file_path = self.data_dir / file_name
            status = "✅" if file_path.exists() else "❌"
            size = f" ({file_path.stat().st_size} bytes)" if file_path.exists() else ""
            self.log(f"   {status} {file_name}{size}")

        # Check recent posts
        recent_posts = list(self.posts_dir.glob('*.md'))
        self.log(f"\n📝 Recent Posts: {len(recent_posts)} found")

        if recent_posts:
            # Show newest posts
            recent_posts.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            self.log("   Latest posts:")
            for post in recent_posts[:5]:
                self.log(f"     - {post.name}")

        # Show last execution summary if available
        summary_file = self.data_dir / 'last_execution_summary.json'
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    summary = json.load(f)

                self.log(f"\n🕐 Last Execution: {summary.get('execution_time', 'Unknown')}")
                self.log(f"   Success Rate: {summary.get('success_rate', 'Unknown')}")
                self.log(f"   Steps: {summary.get('successful_steps', 0)}/{summary.get('total_steps', 0)}")

                # Show failed steps if any
                failed_steps = [r for r in summary.get('results', []) if not r.get('success')]
                if failed_steps:
                    self.log("   Failed steps:")
                    for step in failed_steps:
                        self.log(f"     ❌ {step.get('name', 'Unknown')}")

            except Exception as e:
                self.log(f"\n❌ Could not read last execution summary: {e}")

def main():
    """Main execution with command line arguments"""
    import argparse

    parser = argparse.ArgumentParser(description='Gossip Blog Automation Orchestrator')
    parser.add_argument('--full', action='store_true', help='Run full pipeline')
    parser.add_argument('--step', type=str, help='Run single step by name or script')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--force', action='store_true', help='Continue even if required steps fail')
    parser.add_argument('--hourly', action='store_true', help='Run only hourly tasks')
    parser.add_argument('--daily', action='store_true', help='Run only daily tasks')
    parser.add_argument('--weekly', action='store_true', help='Run only weekly tasks')

    args = parser.parse_args()

    orchestrator = GossipBlogOrchestrator()

    if args.status:
        orchestrator.show_status()
    elif args.step:
        orchestrator.run_single_step(args.step)
    elif args.hourly:
        orchestrator.run_full_pipeline(frequency_filter='hourly')
    elif args.daily:
        orchestrator.run_full_pipeline(frequency_filter='daily')
    elif args.weekly:
        orchestrator.run_full_pipeline(frequency_filter='weekly')
    elif args.full:
        orchestrator.run_full_pipeline(force_all=args.force)
    else:
        # Default: show status and available commands
        orchestrator.show_status()
        print("\n🚀 Usage Examples:")
        print("  python scripts/run_all.py --full              # Run everything")
        print("  python scripts/run_all.py --hourly            # Run hourly tasks")
        print("  python scripts/run_all.py --daily             # Run daily tasks")
        print("  python scripts/run_all.py --step scraper      # Run single step")
        print("  python scripts/run_all.py --status            # Show status")

if __name__ == '__main__':
    main()
