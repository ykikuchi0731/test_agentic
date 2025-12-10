"""Remove div elements with class 'mce-toc' from HTML files."""
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def remove_toc_from_html(html_file: Path) -> Dict[str, Any]:
    """
    Remove all <div class="mce-toc"> elements from an HTML file.

    Args:
        html_file: Path to HTML file

    Returns:
        Dictionary with processing results
    """
    result = {
        'file': str(html_file),
        'toc_found': False,
        'toc_removed_count': 0,
        'error': None
    }

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all div elements with class 'mce-toc'
        toc_divs = soup.find_all('div', class_='mce-toc')

        if toc_divs:
            result['toc_found'] = True
            result['toc_removed_count'] = len(toc_divs)

            # Remove all matched div elements
            for toc_div in toc_divs:
                toc_div.decompose()

            # Write modified HTML back to file
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            logger.info(f"Removed {len(toc_divs)} mce-toc div(s) from: {html_file.name}")

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error processing {html_file}: {e}")

    return result


def process_folder(input_folder: str, recursive: bool = True) -> Dict[str, Any]:
    """
    Process all HTML files in a folder and remove mce-toc divs.

    Args:
        input_folder: Path to folder containing HTML files
        recursive: Whether to process subdirectories

    Returns:
        Dictionary with processing statistics and results
    """
    folder_path = Path(input_folder)

    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {input_folder}")

    if not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {input_folder}")

    # Find all HTML files
    if recursive:
        html_files = list(folder_path.rglob('*.html'))
    else:
        html_files = list(folder_path.glob('*.html'))

    logger.info(f"Found {len(html_files)} HTML files in {input_folder}")

    stats = {
        'total_files': len(html_files),
        'files_with_toc': 0,
        'total_toc_removed': 0,
        'errors': 0
    }

    results = []

    for html_file in html_files:
        result = remove_toc_from_html(html_file)

        if result['toc_found']:
            stats['files_with_toc'] += 1
            stats['total_toc_removed'] += result['toc_removed_count']
            results.append(result)

        if result['error']:
            stats['errors'] += 1

    return {
        'stats': stats,
        'results': results
    }


def save_report_to_csv(results: List[Dict[str, Any]], output_path: str) -> str:
    """
    Save processing results to CSV file.

    Args:
        results: List of processing result dictionaries
        output_path: Path to output CSV file

    Returns:
        Path to created CSV file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'toc_removed_count', 'error'])
        writer.writeheader()

        for result in results:
            writer.writerow({
                'file': result['file'],
                'toc_removed_count': result['toc_removed_count'],
                'error': result.get('error', '')
            })

    logger.info(f"Saved report with {len(results)} entries to: {output_file}")
    return str(output_file)


def main(input_folder: str, output_file: str = None, recursive: bool = True) -> Dict[str, Any]:
    """
    Main function to remove mce-toc divs from HTML files.

    Args:
        input_folder: Path to folder containing HTML files
        output_file: Optional output CSV path (auto-generated if not provided)
        recursive: Whether to process subdirectories

    Returns:
        Dictionary with results
    """
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f'toc_removed_{timestamp}.csv')

    # Process folder
    processing_result = process_folder(input_folder, recursive=recursive)

    stats = processing_result['stats']
    results = processing_result['results']

    # Save report only if there were files with TOC
    csv_path = None
    if results:
        csv_path = save_report_to_csv(results, output_file)

    return {
        'success': True,
        'stats': stats,
        'csv_path': csv_path
    }


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Remove div elements with class "mce-toc" from HTML files'
    )
    parser.add_argument(
        'input_folder',
        help='Path to folder containing HTML files'
    )
    parser.add_argument(
        '--output',
        help='Output CSV file path (default: analysis_output/toc_removed_TIMESTAMP.csv)'
    )
    parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='Do not process subdirectories (recursive is default)'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        result = main(args.input_folder, args.output, args.recursive)

        stats = result['stats']
        print(f"\n{'='*80}")
        print("✅ TOC Removal Complete")
        print('='*80)
        print(f"Total HTML files:     {stats['total_files']}")
        print(f"Files with mce-toc:   {stats['files_with_toc']}")
        print(f"Total TOC removed:    {stats['total_toc_removed']}")
        print(f"Errors:               {stats['errors']}")

        if result['csv_path']:
            print(f"\n📄 Report saved to: {result['csv_path']}")
        else:
            print("\nNo mce-toc elements found in any files.")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
