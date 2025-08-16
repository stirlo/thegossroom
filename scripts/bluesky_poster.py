import os
import yaml
import logging
from datetime import datetime, timezone
from pathlib import Path
import re
from atproto import Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def clean_yaml_frontmatter(content):
    """Clean and fix common YAML frontmatter issues"""
    lines = content.split('\n')

    if not (lines[0].strip() == '---' and '---' in lines[1:]):
        return content

    # Find frontmatter boundaries
    try:
        end_idx = lines[1:].index('---') + 1
        frontmatter_lines = lines[1:end_idx]
        body_lines = lines[end_idx + 1:]
    except ValueError:
        return content

    # Clean frontmatter lines
    cleaned_lines = []
    for line in frontmatter_lines:
        # Fix title quotes
        if line.strip().startswith('title:'):
            # Extract title content
            title_content = line.split('title:', 1)[1].strip()
            # Remove problematic quotes and re-quote properly
            title_content = title_content.strip('\'"')
            title_content = title_content.replace('"', '\\"')
            cleaned_lines.append(f'title: "{title_content}"')
        # Skip recovery data mixed in frontmatter
        elif 'recovered:' in line or 'recovery_date:' in line:
            continue
        # Fix mentions format
        elif line.strip().startswith('mentions:'):
            mentions_content = line.split('mentions:', 1)[1].strip()
            # If it looks like Python dict, keep it
            if mentions_content.startswith('{') and mentions_content.endswith('}'):
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    # Reconstruct content
    return '---\n' + '\n'.join(cleaned_lines) + '\n---\n' + '\n'.join(body_lines)

def parse_post_safely(file_path):
    """Safely parse a post file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Clean the content first
        content = clean_yaml_frontmatter(content)

        # Split frontmatter and body
        if not content.startswith('---'):
            logger.warning(f"No frontmatter found in {file_path}")
            return None

        parts = content.split('---', 2)
        if len(parts) < 3:
            logger.warning(f"Invalid frontmatter structure in {file_path}")
            return None

        frontmatter_text = parts[1]
        body = parts[2].strip()

        # Parse YAML with safe loader
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if not frontmatter:
                frontmatter = {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return None

        return {
            'frontmatter': frontmatter,
            'body': body,
            'file_path': file_path
        }

    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None

def get_unposted_articles():
    """Get articles that haven't been posted to Bluesky yet"""
    posts_dir = Path('_posts')
    unposted = []

    if not posts_dir.exists():
        logger.warning("_posts directory not found")
        return unposted

    for post_file in posts_dir.glob('*.md'):
        # Skip recovered files that might be corrupted
        if 'recovered' in post_file.name:
            logger.info(f"⚠️ Skipping recovered file: {post_file.name}")
            continue

        post_data = parse_post_safely(post_file)
        if not post_data:
            continue

        frontmatter = post_data['frontmatter']

        # Skip if already posted to Bluesky
        if frontmatter.get('bluesky_posted'):
            continue

        # Skip if no title
        if not frontmatter.get('title'):
            logger.warning(f"No title found in {post_file}")
            continue

        # Calculate temperature
        temperature = frontmatter.get('temperature', 0)

        # Only post hot content (temperature >= 25)
        if temperature < 25:
            continue

        unposted.append({
            'file_path': post_file,
            'title': frontmatter['title'],
            'temperature': temperature,
            'date': frontmatter.get('date'),
            'url': f"https://thegossroom.com{frontmatter.get('permalink', '')}"
        })

    # Sort by temperature (hottest first)
    unposted.sort(key=lambda x: x['temperature'], reverse=True)
    return unposted

def create_bluesky_post(article):
    """Create a Bluesky post from article data"""
    title = article['title']
    temp = article['temperature']
    url = article['url']

    # Temperature emoji mapping
    temp_emoji = "🔥" if temp >= 40 else "🌶️" if temp >= 30 else "📈"

    # Create post text
    post_text = f"{temp_emoji} {title}\n\nTemperature: {temp}°\n\n{url}\n\n#GossipRoom #CelebrityNews"

    # Bluesky has a 300 character limit
    if len(post_text) > 300:
        # Truncate title if needed
        max_title_length = 300 - len(f"{temp_emoji} \n\nTemperature: {temp}°\n\n{url}\n\n#GossipRoom #CelebrityNews")
        if max_title_length > 10:
            title = title[:max_title_length-3] + "..."
            post_text = f"{temp_emoji} {title}\n\nTemperature: {temp}°\n\n{url}\n\n#GossipRoom #CelebrityNews"

    return post_text

def mark_as_posted(file_path):
    """Mark an article as posted to Bluesky"""
    try:
        post_data = parse_post_safely(file_path)
        if not post_data:
            return False

        # Add bluesky_posted flag
        post_data['frontmatter']['bluesky_posted'] = True
        post_data['frontmatter']['bluesky_posted_date'] = datetime.now(timezone.utc).isoformat()

        # Reconstruct file content
        frontmatter_text = yaml.dump(post_data['frontmatter'], default_flow_style=False)
        new_content = f"---\n{frontmatter_text}---\n{post_data['body']}"

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        logger.error(f"Error marking {file_path} as posted: {e}")
        return False

def main():
    logger.info("🐦 Starting Bluesky Poster...")

    # Get credentials
    handle = os.getenv('BLUESKY_HANDLE')
    password = os.getenv('BLUESKY_PASSWORD')

    if not handle or not password:
        logger.error("❌ Missing Bluesky credentials")
        return

    try:
        # Initialize Bluesky client
        client = Client()
        client.login(handle, password)
        logger.info("✅ Authenticated with Bluesky")

        # Get unposted articles
        unposted = get_unposted_articles()

        if not unposted:
            logger.info("❄️ No unposted articles found")
            return

        # Post the hottest article
        article = unposted[0]
        post_text = create_bluesky_post(article)

        logger.info(f"🔥 Posting: {article['title']} (Temp: {article['temperature']}°)")
        logger.info(f"📝 Post text: {post_text}")

        # Send to Bluesky
        response = client.send_post(post_text)

        if response:
            logger.info("✅ Successfully posted to Bluesky!")

            # Mark as posted
            if mark_as_posted(article['file_path']):
                logger.info("✅ Marked article as posted")
            else:
                logger.warning("⚠️ Failed to mark article as posted")
        else:
            logger.error("❌ Failed to post to Bluesky")

    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
