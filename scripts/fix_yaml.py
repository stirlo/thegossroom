import os
import re
import yaml
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def fix_yaml_frontmatter(content):
    """Fix all YAML front matter issues"""
    lines = content.split('\n')

    # Find front matter boundaries
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if line.strip() == '---':
            if start_idx is None:
                start_idx = i
            else:
                end_idx = i
                break

    if start_idx is None:
        logger.warning("No front matter start found")
        return content

    # Extract front matter and content
    if end_idx is None:
        # Missing closing ---
        logger.info("Missing closing --- delimiter")
        yaml_lines = lines[start_idx + 1:]
        post_content = ""

        # Find where YAML ends and content begins
        yaml_end = len(yaml_lines)
        for i, line in enumerate(yaml_lines):
            # Look for content that's clearly not YAML
            if (line.strip() and 
                not line.startswith(' ') and 
                not ':' in line and 
                not line.startswith('-') and
                not line.startswith('tags:') and
                not line.startswith('mentions:') and
                not line.startswith('categories:') and
                not re.match(r'^[a-zA-Z_]+:', line)):
                yaml_end = i
                break

        yaml_content = '\n'.join(yaml_lines[:yaml_end])
        post_content = '\n'.join(yaml_lines[yaml_end:])
    else:
        yaml_content = '\n'.join(lines[start_idx + 1:end_idx])
        post_content = '\n'.join(lines[end_idx + 1:])

    # Fix YAML content
    fixed_yaml = fix_yaml_content(yaml_content)

    # Reconstruct file
    result = "---\n" + fixed_yaml + "\n---\n"
    if post_content.strip():
        result += "\n" + post_content.strip()

    return result

def fix_yaml_content(yaml_content):
    """Fix YAML syntax issues"""
    lines = yaml_content.split('\n')
    fixed_lines = []

    for line in lines:
        original_line = line

        # Skip empty lines
        if not line.strip():
            fixed_lines.append(line)
            continue

        # Fix mentions field
        if line.strip().startswith('mentions:'):
            line = fix_mentions_field(line)

        # Fix tags field
        elif line.strip().startswith('tags:'):
            line = fix_tags_field(line)

        # Fix categories field
        elif line.strip().startswith('categories:'):
            line = fix_categories_field(line)

        # Fix title field (missing quotes)
        elif line.strip().startswith('title:'):
            line = fix_title_field(line)

        # Fix source_url field
        elif line.strip().startswith('source_url:'):
            line = fix_url_field(line)

        # Fix source field (extra quotes)
        elif line.strip().startswith('source:'):
            line = fix_source_field(line)

        # Remove any content that leaked into YAML
        elif is_content_not_yaml(line):
            logger.info(f"Removing content from YAML: {line[:50]}...")
            continue

        if line != original_line:
            logger.info(f"Fixed: {original_line.strip()} -> {line.strip()}")

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_mentions_field(line):
    """Fix mentions field format"""
    # Extract the mentions part
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # Handle dictionary format {'key': value} -> ['key']
    if value.startswith('{') and value.endswith('}'):
        # Extract keys from dictionary
        dict_content = value[1:-1]  # Remove { }

        # Handle various dictionary formats
        keys = []
        if dict_content.strip():
            # Split by comma and extract keys
            items = dict_content.split(',')
            for item in items:
                if ':' in item:
                    key_part = item.split(':')[0].strip()
                    # Remove quotes (both single and double, including extra quotes)
                    key_part = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', key_part)
                    if key_part:
                        keys.append(key_part)

        # Convert to array format
        if keys:
            keys_str = "', '".join(keys)
            return f"{key}: ['{keys_str}']"
        else:
            return f"{key}: []"

    # Handle already correct array format
    elif value.startswith('[') and value.endswith(']'):
        return line

    # Handle single value
    else:
        # Remove quotes and wrap in array
        clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)
        if clean_value:
            return f"{key}: ['{clean_value}']"
        else:
            return f"{key}: []"

def fix_tags_field(line):
    """Fix tags field format"""
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # Ensure proper array format with quotes
    if not value.startswith('['):
        # Single tag
        clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)
        return f"{key}: ['{clean_value}']"

    # Already array format - ensure quotes are correct
    return line

def fix_categories_field(line):
    """Fix categories field format"""
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # Simple string value
    if not value.startswith('['):
        clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)
        return f"{key}: {clean_value}"

    return line

def fix_title_field(line):
    """Fix title field - ensure proper quoting"""
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # If not quoted, add quotes
    if not (value.startswith('"') and value.endswith('"')):
        # Remove existing quotes first
        clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)
        return f'{key}: "{clean_value}"'

    return line

def fix_url_field(line):
    """Fix URL field - ensure proper quoting and fix broken URLs"""
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # Remove quotes to clean URL
    clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)

    # Fix broken URLs with spaces
    clean_value = re.sub(r'\s+=\s*', '=', clean_value)  # Fix " =1490 _campaign" -> "=1490_campaign"
    clean_value = re.sub(r'\s+_', '_', clean_value)     # Fix spaces before underscores
    clean_value = re.sub(r'\s+', '', clean_value)       # Remove any remaining spaces

    return f'{key}: "{clean_value}"'

def fix_source_field(line):
    """Fix source field - remove extra quotes"""
    if ':' not in line:
        return line

    key, value = line.split(':', 1)
    value = value.strip()

    # Remove extra quotes
    clean_value = re.sub(r'^["\']*(.*?)["\'"]*$', r'\1', value)
    return f"{key}: {clean_value}"

def is_content_not_yaml(line):
    """Detect if line is content that leaked into YAML"""
    line = line.strip()
    if not line:
        return False

    # Content indicators
    content_patterns = [
        r'^\*\*.*\*\*',  # Bold text
        r'^[A-Z][^:]*\s+[a-z]',  # Sentence-like text
        r'^\[.*\]\(.*\)',  # Markdown links
        r'^Read full article',  # Common content phrase
        r'^This post was',  # Common content phrase
        r'^\*.*\*$',  # Italic text
    ]

    for pattern in content_patterns:
        if re.match(pattern, line):
            return True

    return False

def process_markdown_file(file_path):
    """Process a single markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixed_content = fix_yaml_frontmatter(content)

        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            logger.info(f"✅ Fixed: {file_path.name}")
            return True
        else:
            logger.info(f"⚪ No changes needed: {file_path.name}")
            return False

    except Exception as e:
        logger.error(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all markdown files"""
    posts_dir = Path('_posts')

    if not posts_dir.exists():
        logger.error("❌ _posts directory not found!")
        return

    markdown_files = list(posts_dir.glob('*.md'))

    if not markdown_files:
        logger.warning("⚠️ No markdown files found in _posts directory")
        return

    logger.info(f"🔧 Processing {len(markdown_files)} markdown files...")

    fixed_count = 0
    total_count = len(markdown_files)

    for file_path in markdown_files:
        if process_markdown_file(file_path):
            fixed_count += 1

    logger.info(f"🎉 COMPLETE! Fixed {fixed_count}/{total_count} files")

    if fixed_count > 0:
        logger.info("✅ All YAML front matter issues should now be resolved!")
        logger.info("✅ Missing closing --- delimiters added")
        logger.info("✅ Mentions fields converted to proper arrays")
        logger.info("✅ Tags fields properly formatted")
        logger.info("✅ Broken URLs fixed")
        logger.info("✅ Content separated from YAML")
        logger.info("✅ Quote issues resolved")
    else:
        logger.info("⚪ No files needed fixing - all good!")

if __name__ == "__main__":
    main()
