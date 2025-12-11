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

    # Pattern for successful downloads (new format)
    pattern_success = re.compile(
        r"Downloaded Google Doc: '([^']+)' \| File: ([^\|]+) \| URL: ([^\|]+) \| Article: ([^\n]+)"
    )

    # Pattern for failed downloads (new format)
    pattern_failed = re.compile(
        r"Failed to download Google Doc: '([^']+)' \| File: ([^\|]+) \| URL: ([^\|]+) \| Article: ([^\|]+) \| Error: ([^\n]+)"
    )

    # Pattern for old success format
    pattern_old = re.compile(
        r"Downloaded Google Doc to: ([^\|]+) \| Article: ([^(]+)\(([^)]+)\) \| Google Doc ID: ([a-zA-Z0-9_-]+)"
    )

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'Google Doc' not in line:
                continue

            # Try success pattern first
            match = pattern_success.search(line)
            if match:
                doc_title = match.group(1).strip()
                filename = match.group(2).strip()
                url = match.group(3).strip()
                article = match.group(4).strip()

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

                mappings.append({
                    'File': filename,
                    'URL': url,
                    'Article': article,
                    'Status': 'Failed',
                    'Error': error
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
                    'Article': article,
                    'Status': 'Success',
                    'Error': ''
                })

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

    # Count success/failed
    success_count = sum(1 for m in mappings if m['Status'] == 'Success')
    failed_count = sum(1 for m in mappings if m['Status'] == 'Failed')

    return {
        'success': True,
        'csv_path': csv_path,
        'count': len(mappings),
        'success_count': success_count,
        'failed_count': failed_count
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
