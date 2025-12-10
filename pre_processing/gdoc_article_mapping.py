"""Extract Google Docs mapping from migration logs."""
import re
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def extract_gdoc_mapping_from_log(log_file_path: str) -> List[Dict[str, str]]:
    """
    Extract Google Docs mapping from migration log file.

    Parses log entries like:
    "Downloaded Google Doc: 'title' | File: filename.docx | URL: https://... | Article: KB0010400 (title)"

    Args:
        log_file_path: Path to migration log file

    Returns:
        List of dictionaries with File, URL, Article keys
    """
    log_path = Path(log_file_path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_file_path}")

    mappings = []

    # Pattern for new log format (after our changes)
    pattern_new = re.compile(
        r"Downloaded Google Doc: '([^']+)' \| File: ([^\|]+) \| URL: ([^\|]+) \| Article: ([^\n]+)"
    )

    # Pattern for old log format
    pattern_old = re.compile(
        r"Downloaded Google Doc to: ([^\|]+) \| Article: ([^(]+)\(([^)]+)\) \| Google Doc ID: ([a-zA-Z0-9_-]+)"
    )

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'Downloaded Google Doc' not in line:
                continue

            # Try new format first
            match = pattern_new.search(line)
            if match:
                doc_title = match.group(1).strip()
                filename = match.group(2).strip()
                url = match.group(3).strip()
                article = match.group(4).strip()

                mappings.append({
                    'File': filename,
                    'URL': url,
                    'Article': article
                })
                continue

            # Try old format
            match = pattern_old.search(line)
            if match:
                file_path = match.group(1).strip()
                article_number = match.group(2).strip()
                article_title = match.group(3).strip()
                doc_id = match.group(4).strip()

                filename = Path(file_path).name
                url = f"https://docs.google.com/document/d/{doc_id}/edit"
                article = f"{article_number} ({article_title})"

                mappings.append({
                    'File': filename,
                    'URL': url,
                    'Article': article
                })

    logger.info(f"Extracted {len(mappings)} Google Docs mappings from log")
    return mappings


def save_mapping_to_csv(mappings: List[Dict[str, str]], output_path: str) -> str:
    """
    Save Google Docs mappings to CSV file.

    Args:
        mappings: List of mapping dictionaries
        output_path: Path to output CSV file

    Returns:
        Path to created CSV file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['File', 'URL', 'Article'])
        writer.writeheader()
        writer.writerows(mappings)

    logger.info(f"Saved {len(mappings)} mappings to: {output_file}")
    return str(output_file)


def main(log_file: str, output_file: str = None) -> Dict[str, Any]:
    """
    Main function to extract and save Google Docs mapping.

    Args:
        log_file: Path to migration log file
        output_file: Optional output CSV path (auto-generated if not provided)

    Returns:
        Dictionary with results
    """
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f'gdoc_article_mapping_{timestamp}.csv')

    # Extract mappings from log
    mappings = extract_gdoc_mapping_from_log(log_file)

    if not mappings:
        logger.warning("No Google Docs mappings found in log file")
        return {
            'success': False,
            'error': 'No Google Docs mappings found',
            'count': 0
        }

    # Save to CSV
    csv_path = save_mapping_to_csv(mappings, output_file)

    return {
        'success': True,
        'csv_path': csv_path,
        'count': len(mappings)
    }


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract Google Docs mapping from migration log'
    )
    parser.add_argument(
        'log_file',
        help='Path to migration log file (e.g., logs/migration_20251210_103001.log)'
    )
    parser.add_argument(
        '--output',
        help='Output CSV file path (default: analysis_output/gdoc_article_mapping_TIMESTAMP.csv)'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        result = main(args.log_file, args.output)

        if result['success']:
            print(f"\n✅ Successfully extracted {result['count']} Google Docs mappings")
            print(f"📄 CSV saved to: {result['csv_path']}")
        else:
            print(f"\n❌ {result['error']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
