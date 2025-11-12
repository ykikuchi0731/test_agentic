"""HTML parsing utilities for ServiceNow knowledge articles."""
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class HTMLParser:
    """Parser for HTML content from ServiceNow knowledge articles."""
    
    def __init__(self):
        """Initialize HTML parser."""
        self.parser = 'lxml'
    
    def parse_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract structured data.
        
        Args:
            html_content: HTML string from knowledge article
            
        Returns:
            Dictionary containing parsed content:
                - text: Plain text content
                - images: List of image sources
                - links: List of hyperlinks
                - tables: List of HTML tables
                - headings: List of headings with levels
        """
        if not html_content:
            return self._empty_result()
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            return {
                'text': self.extract_text(soup),
                'images': self.extract_images(soup),
                'links': self.extract_links(soup),
                'tables': self.extract_tables(soup),
                'headings': self.extract_headings(soup),
                'lists': self.extract_lists(soup),
                'code_blocks': self.extract_code_blocks(soup)
            }
        
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return self._empty_result()
    
    def extract_text(self, soup: BeautifulSoup) -> str:
        """
        Extract plain text from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Plain text content
        """
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Get text and clean up whitespace
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract image information from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries with image data (src, alt, title)
        """
        images = []
        
        for img in soup.find_all('img'):
            image_data = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            }
            images.append(image_data)
        
        return images
    
    def extract_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract hyperlinks from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries with link data (url, text)
        """
        links = []
        
        for link in soup.find_all('a', href=True):
            link_data = {
                'url': link.get('href', ''),
                'text': link.get_text(strip=True),
                'title': link.get('title', '')
            }
            links.append(link_data)
        
        return links
    
    def extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract tables from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries representing tables
        """
        tables = []
        
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [th.get_text(strip=True) for th in headers]
            
            # Extract rows
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_data['rows'].append(row_data)
            
            tables.append(table_data)
        
        return tables
    
    def extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract headings from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries with heading data (level, text)
        """
        headings = []
        
        for level in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{level}'):
                heading_data = {
                    'level': level,
                    'text': heading.get_text(strip=True)
                }
                headings.append(heading_data)
        
        return headings
    
    def extract_lists(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract lists from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries with list data (type, items)
        """
        lists = []
        
        for list_tag in soup.find_all(['ul', 'ol']):
            list_data = {
                'type': 'ordered' if list_tag.name == 'ol' else 'unordered',
                'items': [li.get_text(strip=True) for li in list_tag.find_all('li', recursive=False)]
            }
            lists.append(list_data)
        
        return lists
    
    def extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract code blocks from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of dictionaries with code block data
        """
        code_blocks = []
        
        # Extract pre/code blocks
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                code_blocks.append({
                    'language': code.get('class', [''])[0] if code.get('class') else '',
                    'content': code.get_text()
                })
            else:
                code_blocks.append({
                    'language': '',
                    'content': pre.get_text()
                })
        
        return code_blocks
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'text': '',
            'images': [],
            'links': [],
            'tables': [],
            'headings': [],
            'lists': [],
            'code_blocks': []
        }
    
    def html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to Markdown format.
        
        Args:
            html_content: HTML string
            
        Returns:
            Markdown formatted string
        """
        parsed = self.parse_html(html_content)
        markdown_parts = []
        
        # Add headings
        for heading in parsed['headings']:
            level = heading['level']
            markdown_parts.append(f"{'#' * level} {heading['text']}\n")
        
        # Add main text
        if parsed['text']:
            markdown_parts.append(parsed['text'])
        
        # Add links
        if parsed['links']:
            markdown_parts.append("\n## Links\n")
            for link in parsed['links']:
                markdown_parts.append(f"- [{link['text']}]({link['url']})")
        
        # Add images
        if parsed['images']:
            markdown_parts.append("\n## Images\n")
            for img in parsed['images']:
                alt_text = img['alt'] or 'Image'
                markdown_parts.append(f"![{alt_text}]({img['src']})")
        
        return '\n'.join(markdown_parts)

