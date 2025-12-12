"""Extract Google Docs mapping from migration logs and tracking files."""
import re
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def extract_gdoc_mapping_from_tracking_files(download_dir: str, log_file_path: str = None) -> Tuple[List[Dict[str, str]], set]:
    """
    Extract Google Docs mapping from tracking files (primary source of truth).

    Each downloaded file has a companion .tracking.json file that contains:
    - download_id: Unique ID for this download
    - file_id: Google Docs file ID
    - doc_title: Document title
    - downloaded_filename: Name of the downloaded file
    - download_timestamp: When the download completed

    To get the article information, we parse the log file for context.

    Args:
        download_dir: Directory containing downloaded files and tracking files
        log_file_path: Optional path to log file for article context

    Returns:
        Tuple of (mappings list, set of processed file_ids)
    """
    download_path = Path(download_dir)
    if not download_path.exists():
        logger.warning(f"Download directory not found: {download_dir}")
        return [], set()

    mappings = []
    processed_file_ids = set()

    # Build file_id -> article mapping from log if available
    file_id_to_article = {}
    if log_file_path:
        log_path = Path(log_file_path)
        if log_path.exists():
            pattern = re.compile(
                r"(Downloaded Google Doc|Failed to download Google Doc): '([^']+)' \| File: ([^\|]+) \| URL: https://docs\.google\.com/document/d/([^/]+)/edit \| Article: ([^\n|]+)"
            )
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        file_id = match.group(4).strip()
                        article = match.group(5).strip()
                        file_id_to_article[file_id] = article

    # Process all tracking files
    tracking_files = list(download_path.glob("*.tracking.json"))
    logger.info(f"Found {len(tracking_files)} tracking files in {download_dir}")

    for tracking_file in tracking_files:
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)

            file_id = tracking_data.get('file_id')
            downloaded_filename = tracking_data.get('downloaded_filename')
            doc_title = tracking_data.get('doc_title', 'Unknown')

            if not file_id or not downloaded_filename:
                logger.warning(f"Incomplete tracking data in {tracking_file.name}")
                continue

            # Check if file actually exists
            downloaded_file = download_path / downloaded_filename
            if not downloaded_file.exists():
                logger.warning(f"Tracked file does not exist: {downloaded_filename}")
                continue

            # Get article info from log mapping
            article = file_id_to_article.get(file_id, 'Unknown')
            url = f"https://docs.google.com/document/d/{file_id}/edit"

            mappings.append({
                'File': downloaded_filename,
                'URL': url,
                'Article': article,
                'Status': 'Success',
                'Error': ''
            })

            processed_file_ids.add(file_id)

        except Exception as e:
            logger.error(f"Error processing tracking file {tracking_file.name}: {e}")
            continue

    logger.info(f"Extracted {len(mappings)} mappings from tracking files")
    return mappings, processed_file_ids


def extract_gdoc_mapping_from_log(log_file_path: str) -> List[Dict[str, str]]:
    """
    Extract Google Docs mapping from migration log file.

    Parses both successful and failed download log entries:
    - Success: "Downloaded Google Doc: 'title' | File: filename.docx | URL: https://... | Article: KB0010400 (title)"
    - Failure: "Failed to download Google Doc: 'title' | File: N/A | URL: https://... | Article: KB0010400 (title) | Error: ..."

    Args:
        log_file_path: Path to migration log file

    Returns:
        List of dictionaries with File, URL, Article, Status, Error keys
    """
    log_path = Path(log_file_path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_file_path}")

    mappings = []
    seen_combinations = set()  # Track (url, article) to avoid duplicates

    # Pattern for successful downloads (new format - preferred)
    pattern_success = re.compile(
        r"Downloaded Google Doc: '([^']+)' \| File: ([^\|]+) \| URL: ([^\|]+) \| Article: ([^\n]+)"
    )

    # Pattern for failed downloads (new format)
    pattern_failed = re.compile(
        r"Failed to download Google Doc: '([^']+)' \| File: ([^\|]+) \| URL: ([^\|]+) \| Article: ([^\|]+) \| Error: ([^\n]+)"
    )

    # Pattern for old success format (skip to avoid duplicates with new format)
    pattern_old_skip = re.compile(
        r"✅ Downloaded Google Doc to:"
    )

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'Google Doc' not in line:
                continue

            # Skip old format lines (they duplicate new format)
            if pattern_old_skip.search(line):
                continue

            # Try success pattern first
            match = pattern_success.search(line)
            if match:
                doc_title = match.group(1).strip()
                filename = match.group(2).strip()
                url = match.group(3).strip()
                article = match.group(4).strip()

                # Check for duplicates
                combination = (url, article)
                if combination in seen_combinations:
                    continue
                seen_combinations.add(combination)

                mappings.append({
                    'File': filename,
                    'URL': url,
                    'Article': article,
                    'Status': 'Success',
                    'Error': ''
                })
                continue

            # Try failed pattern
            match = pattern_failed.search(line)
            if match:
                doc_title = match.group(1).strip()
                filename = match.group(2).strip()
                url = match.group(3).strip()
                article = match.group(4).strip()
                error = match.group(5).strip()

                # Check for duplicates
                combination = (url, article)
                if combination in seen_combinations:
                    continue
                seen_combinations.add(combination)

                mappings.append({
                    'File': filename,
                    'URL': url,
                    'Article': article,
                    'Status': 'Failed',
                    'Error': error
                })
                continue

    success_count = sum(1 for m in mappings if m['Status'] == 'Success')
    failed_count = sum(1 for m in mappings if m['Status'] == 'Failed')
    logger.info(f"Extracted {len(mappings)} Google Docs mappings from log (Success: {success_count}, Failed: {failed_count})")
    return mappings


def extract_gdoc_mapping_from_export_report(report_csv_path: str) -> List[Dict[str, str]]:
    """
    Extract Google Docs mapping from export report CSV.

    This is more reliable than log parsing since the export report contains
    structured data about all Google Docs downloads (both successful and failed).

    Args:
        report_csv_path: Path to export report CSV file

    Returns:
        List of dictionaries with File, URL, Article, Status, Error keys
    """
    report_path = Path(report_csv_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Export report not found: {report_csv_path}")

    mappings = []

    with open(report_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only process DOCX export rows (Google Docs)
            if row.get('export_type') != 'DOCX':
                continue

            google_docs_urls = row.get('google_docs_urls', '').strip()
            if not google_docs_urls:
                continue

            # Parse URLs (may be semicolon-separated)
            urls = [url.strip() for url in google_docs_urls.split(';') if url.strip()]

            article_number = row.get('article_number', '')
            article_title = row.get('article_title', '')
            article = f"{article_number} ({article_title})"
            status = row.get('status', 'Unknown')
            error = row.get('error_message', '')

            # Create mapping for each URL
            for url in urls:
                # TODO: We don't have filename info in export report for individual docs
                # This needs to be enhanced
                mappings.append({
                    'File': 'N/A',  # Not available in export report
                    'URL': url,
                    'Article': article,
                    'Status': 'Success' if status == 'success' else 'Failed',
                    'Error': error
                })

    success_count = sum(1 for m in mappings if m['Status'] == 'Success')
    failed_count = sum(1 for m in mappings if m['Status'] == 'Failed')
    logger.info(f"Extracted {len(mappings)} Google Docs mappings from export report (Success: {success_count}, Failed: {failed_count})")
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
        writer = csv.DictWriter(f, fieldnames=['File', 'URL', 'Article', 'Status', 'Error'])
        writer.writeheader()
        writer.writerows(mappings)

    logger.info(f"Saved {len(mappings)} mappings to: {output_file}")
    return str(output_file)


def main(log_file: str, output_file: str = None, download_dir: str = 'download') -> Dict[str, Any]:
    """
    Main function to extract and save Google Docs mapping.

    Uses tracking files as the primary source of truth (deterministic),
    with log parsing as fallback for failed downloads.

    Args:
        log_file: Path to migration log file
        output_file: Optional output CSV path (auto-generated if not provided)
        download_dir: Directory containing downloaded files and tracking files

    Returns:
        Dictionary with results
    """
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f'gdoc_article_mapping_{timestamp}.csv')

    # Extract mappings from tracking files (primary source - deterministic)
    mappings_from_tracking, processed_file_ids = extract_gdoc_mapping_from_tracking_files(
        download_dir, log_file
    )
    logger.info(f"Extracted {len(mappings_from_tracking)} successful downloads from tracking files")

    # Extract additional mappings from log (for failed downloads)
    mappings_from_log = extract_gdoc_mapping_from_log(log_file)

    # Filter log mappings to only include:
    # 1. Failed downloads (not in tracking files)
    # 2. Successful downloads not already in tracking files (shouldn't happen but just in case)
    additional_mappings = [
        m for m in mappings_from_log
        if m['Status'] == 'Failed' or (
            # Extract file_id from URL to check if already processed
            (file_id := m['URL'].split('/d/')[-1].split('/')[0]) and
            file_id not in processed_file_ids
        )
    ]

    logger.info(f"Found {len(additional_mappings)} additional entries from log (failed downloads)")

    # Combine mappings: tracking files first (authoritative), then log entries
    all_mappings = mappings_from_tracking + additional_mappings

    if not all_mappings:
        logger.warning("No Google Docs mappings found")
        return {
            'success': False,
            'error': 'No Google Docs mappings found',
            'count': 0
        }

    # Save to CSV
    csv_path = save_mapping_to_csv(all_mappings, output_file)

    # Count success/failed
    success_count = sum(1 for m in all_mappings if m['Status'] == 'Success')
    failed_count = sum(1 for m in all_mappings if m['Status'] == 'Failed')

    logger.info(f"Total: {len(all_mappings)} mappings ({success_count} successful, {failed_count} failed)")

    return {
        'success': True,
        'csv_path': csv_path,
        'count': len(all_mappings),
        'success_count': success_count,
        'failed_count': failed_count,
        'tracking_file_count': len(mappings_from_tracking),
        'log_only_count': len(additional_mappings)
    }


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract Google Docs mapping from tracking files and migration log'
    )
    parser.add_argument(
        'log_file',
        help='Path to migration log file (e.g., logs/migration_20251210_103001.log)'
    )
    parser.add_argument(
        '--output',
        help='Output CSV file path (default: analysis_output/gdoc_article_mapping_TIMESTAMP.csv)'
    )
    parser.add_argument(
        '--download-dir',
        default='download',
        help='Directory containing downloaded files and tracking files (default: download)'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        result = main(args.log_file, args.output, args.download_dir)

        if result['success']:
            print(f"\n✅ Successfully extracted {result['count']} Google Docs mappings")
            print(f"   - From tracking files: {result['tracking_file_count']} (deterministic)")
            print(f"   - From log (failed): {result['log_only_count']}")
            print(f"   - Success: {result['success_count']}, Failed: {result['failed_count']}")
            print(f"📄 CSV saved to: {result['csv_path']}")
        else:
            print(f"\n❌ {result['error']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
