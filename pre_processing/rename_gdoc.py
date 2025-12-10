"""Rename Google Docs files to article names based on mapping CSV."""
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def validate_mapping_file(mapping_file: Path) -> bool:
    """
    Validate that mapping CSV has required columns.

    Args:
        mapping_file: Path to mapping CSV file

    Returns:
        True if valid, raises exception otherwise
    """
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

    with open(mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if not fieldnames:
            raise ValueError("Mapping file is empty or has no header")

        required_columns = {'File', 'URL', 'Article'}
        if not required_columns.issubset(set(fieldnames)):
            raise ValueError(
                f"Mapping file must have columns: {required_columns}. "
                f"Found: {set(fieldnames)}"
            )

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace characters that are invalid in filenames
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')

    return sanitized


def rename_google_docs(mapping_file_path: str, input_folder: str) -> Dict[str, Any]:
    """
    Rename Google Docs files based on mapping CSV.

    Args:
        mapping_file_path: Path to mapping CSV file
        input_folder: Path to folder containing .docx files

    Returns:
        Dictionary with processing results
    """
    mapping_file = Path(mapping_file_path)
    folder = Path(input_folder)

    # Validate inputs
    validate_mapping_file(mapping_file)

    if not folder.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {input_folder}")

    # Read mapping CSV
    mappings = []
    with open(mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append({
                'file': row['File'],
                'url': row['URL'],
                'article': row['Article']
            })

    logger.info(f"Read {len(mappings)} mappings from CSV")

    # Process each mapping
    results = {
        'total': len(mappings),
        'renamed': 0,
        'not_found': 0,
        'failed': 0,
        'details': []
    }

    for mapping in mappings:
        original_filename = mapping['file']
        article_name = mapping['article']

        # Search for file in input folder
        file_path = folder / original_filename

        result = {
            'original_file': original_filename,
            'article_name': article_name,
            'status': '',
            'new_name': '',
            'error': ''
        }

        if not file_path.exists():
            result['status'] = 'not_found'
            result['error'] = f"File not found: {original_filename}"
            results['not_found'] += 1
            logger.warning(result['error'])
        else:
            try:
                # Create new filename from article name
                sanitized_article = sanitize_filename(article_name)
                new_filename = f"{sanitized_article}.docx"
                new_path = folder / new_filename

                # Check if target already exists
                if new_path.exists() and new_path != file_path:
                    result['status'] = 'failed'
                    result['error'] = f"Target file already exists: {new_filename}"
                    results['failed'] += 1
                    logger.error(result['error'])
                elif new_path == file_path:
                    result['status'] = 'skipped'
                    result['new_name'] = new_filename
                    result['error'] = 'File already has target name'
                    logger.info(f"Skipped (already named): {original_filename}")
                else:
                    # Rename file
                    file_path.rename(new_path)
                    result['status'] = 'renamed'
                    result['new_name'] = new_filename
                    results['renamed'] += 1
                    logger.info(f"Renamed: {original_filename} -> {new_filename}")

            except Exception as e:
                result['status'] = 'failed'
                result['error'] = str(e)
                results['failed'] += 1
                logger.error(f"Failed to rename {original_filename}: {e}")

        results['details'].append(result)

    return results


def save_report(results: Dict[str, Any], output_path: str) -> str:
    """
    Save renaming results to CSV file.

    Args:
        results: Results dictionary from rename_google_docs
        output_path: Path to output CSV file

    Returns:
        Path to created CSV file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['original_file', 'article_name', 'status', 'new_name', 'error']
        )
        writer.writeheader()
        writer.writerows(results['details'])

    logger.info(f"Saved report to: {output_file}")
    return str(output_file)


def main(mapping_file_path: str, input_folder: str, output_file: str = None) -> Dict[str, Any]:
    """
    Main function to rename Google Docs files.

    Args:
        mapping_file_path: Path to mapping CSV file
        input_folder: Path to folder containing .docx files
        output_file: Optional output CSV path (auto-generated if not provided)

    Returns:
        Dictionary with results
    """
    from datetime import datetime

    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f'gdoc_renamed_{timestamp}.csv')

    # Rename files
    results = rename_google_docs(mapping_file_path, input_folder)

    # Save report
    csv_path = save_report(results, output_file)

    return {
        'success': True,
        'stats': {
            'total': results['total'],
            'renamed': results['renamed'],
            'not_found': results['not_found'],
            'failed': results['failed']
        },
        'csv_path': csv_path
    }


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Rename Google Docs files based on article names from mapping CSV'
    )
    parser.add_argument(
        'mapping_file',
        help='Path to mapping CSV file (e.g., analysis_output/gdoc_article_mapping_*.csv)'
    )
    parser.add_argument(
        'input_folder',
        help='Path to folder containing .docx files to rename'
    )
    parser.add_argument(
        '--output',
        help='Output report CSV file path (default: analysis_output/gdoc_renamed_TIMESTAMP.csv)'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        result = main(args.mapping_file, args.input_folder, args.output)

        stats = result['stats']
        print(f"\n{'='*80}")
        print("✅ Google Docs Renaming Complete")
        print('='*80)
        print(f"Total files:      {stats['total']}")
        print(f"Renamed:          {stats['renamed']}")
        print(f"Not found:        {stats['not_found']}")
        print(f"Failed:           {stats['failed']}")
        print(f"\n📄 Report saved to: {result['csv_path']}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
