"""Web scraper for Stardew Valley Wiki content."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin
from collections import deque

import requests
from bs4 import BeautifulSoup

# Import settings with proper path handling
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.settings import settings
except ImportError:
    # Fallback settings if config module not available
    class Settings:
        wiki_base_url = "https://stardewvalleywiki.com"
        scrape_delay = 0.5
        max_concurrent_requests = 5
        scraped_data_file = "./data/wiki_content.json"
    
    settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StardewWikiScraper:
    """
    Scrapes content from the Stardew Valley Wiki using a Breadth-First Search (BFS)
    strategy for comprehensive content discovery, now including image and table data.
    """
    
    def __init__(self, max_pages: int = 1000):
        self.base_url = settings.wiki_base_url
        self.delay = settings.scrape_delay
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.scraped_content: List[Dict] = []
        
        self.seed_pages = [
            "/Stardew_Valley_Wiki", "/Crops", "/Villagers", "/Fishing", 
            "/Mining", "/Community_Center", "/Ginger_Island", "/Monsters",
            "/Quests", "/Achievements", "/Cooking", "/Crafting", "/Foraging"
        ]

    def get_page_content_and_links(self, url: str) -> Optional[Tuple[Dict, Set[str]]]:
        """
        Scrapes content, discovers links, and extracts image URLs and structured tables.
        """
        try:
            full_url = urljoin(self.base_url, url)
            if full_url in self.visited_urls:
                return None
                
            logger.info(f"Scraping: {full_url}")
            self.visited_urls.add(full_url)
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'StardewAIScraper/1.1 (AdvancedDataExtraction)'
            })
            
            response = session.get(full_url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            if response.url != full_url:
                self.visited_urls.add(response.url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('h1', {'class': 'firstHeading'})
            title_text = title.get_text().strip() if title else "Unknown"
            
            content_div = soup.find('div', {'id': 'mw-content-text'})
            if not content_div:
                return None

            # Extract main image from infobox before cleaning
            main_image_url = self._extract_main_image(content_div)

            # Enhanced cleanup to remove non-content elements
            self._cleanup_content(content_div)

            # Remove navigation, footers, and other clutter
            for element in content_div.find_all(['nav', 'aside', 'footer', 'script', 'style', 'div.reflist', 'span.mw-editsection']):
                element.decompose()

            discovered_links = self._discover_wiki_links(content_div)
            
            # Extract structured tables
            tables = [self._extract_table_data(table) for table in content_div.find_all('table', {'class': 'wikitable'}) if self._extract_table_data(table)]

            text_content = content_div.get_text(strip=True, separator='\n')
            
            page_data = {
                'url': response.url,
                'title': title_text,
                'content': text_content,
                'image_url': main_image_url,
                'tables': tables,
                'scraped_at': time.time()
            }
            
            return page_data, discovered_links
            
        except requests.RequestException as e:
            logger.error(f"HTTP Error scraping {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"General Error scraping {url}: {e}")
            return None

    def _cleanup_content(self, content_div: BeautifulSoup):
        """Removes unwanted elements like SVGs, scripts, and decorative icons."""
        # Remove all SVG elements as they are often used for icons or complex graphics
        for svg in content_div.find_all('svg'):
            svg.decompose()
        # Remove script and style tags if any are missed
        for s in content_div.find_all(['script', 'style']):
            s.decompose()
        # Remove elements that are typically non-content, like nav boxes or metadata
        for junk in content_div.find_all(class_=['nomobile', 'mw-editsection', 'plainlinks', 'toc']):
            junk.decompose()
        # Remove any stray images that are not part of the main content (e.g., icons)
        for img in content_div.find_all('img', class_=lambda x: x != 'infobox-img'): # Keep main image
            if not img.find_parent('table', class_='infobox'):
                img.decompose()

    def _extract_main_image(self, content_div: BeautifulSoup) -> Optional[str]:
        """Extracts the main image URL from the infobox."""
        infobox = content_div.find('table', {'class': 'infobox'})
        if not infobox:
            return None
        
        image_tag = infobox.find('img')
        if image_tag and image_tag.get('src'):
            # Construct full URL if relative
            return urljoin(self.base_url, image_tag['src'])
        return None

    def _discover_wiki_links(self, content_div: BeautifulSoup) -> Set[str]:
        """Discover internal wiki links."""
        links = set()
        for link in content_div.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('/') and not href.startswith('//'):
                if not any(prefix in href for prefix in ['File:', 'Template:', 'Help:', 'Special:', 'User_talk:', 'Talk:', 'User:', 'mediawiki/index.php?title=']) and not any(href.endswith(ext) for ext in ['.png', '.jpg', '.gif']):
                    clean_url = href.split('#')[0].split('?')[0]
                    if clean_url and len(clean_url) > 1:
                        links.add(clean_url)
        return links

    def _extract_table_data(self, table: BeautifulSoup) -> Optional[Dict]:
        """Extracts structured data (headers and rows) from a wiki table."""
        try:
            headers = [th.get_text(strip=True) for th in table.find('tr').find_all(['th', 'td'])]
            rows = []
            for row in table.find_all('tr')[1:]:
                # Extract text and handle images within cells
                row_data = []
                for cell in row.find_all(['td', 'th']):
                    img = cell.find('img')
                    if img and img.get('src'):
                        # If cell contains an image, grab its URL
                        row_data.append(urljoin(self.base_url, img['src']))
                    else:
                        row_data.append(cell.get_text(strip=True))
                if any(row_data): # only add if row is not empty
                    rows.append(row_data)

            # Assign a title to the table if one is found immediately preceding it
            caption = table.find('caption')
            table_title = caption.get_text(strip=True) if caption else "Untitled Table"
            
            if headers and rows:
                return {'title': table_title, 'headers': headers, 'rows': rows}
        except Exception as e:
            logger.warning(f"Error extracting table: {e}")
        return None

    def scrape_website(self):
        """Performs a BFS scrape of the wiki."""
        frontier = deque(self.seed_pages)
        logger.info(f"Starting scrape with {len(self.seed_pages)} seed pages. Max pages: {self.max_pages}.")
        
        while frontier and len(self.scraped_content) < self.max_pages:
            current_url = frontier.popleft()
            
            result = self.get_page_content_and_links(current_url)
            
            if result:
                page_data, new_links = result
                self.scraped_content.append(page_data)
                
                logger.info(f"✓ [{len(self.scraped_content)}/{self.max_pages}] Success: {page_data['title']} (Image: {'Yes' if page_data['image_url'] else 'No'}, Tables: {len(page_data['tables'])})")
                
                for link in new_links:
                    full_link_url = urljoin(self.base_url, link)
                    if full_link_url not in self.visited_urls and link not in frontier:
                        frontier.append(link)
            else:
                logger.warning(f"✗ Failed or skipped: {current_url}")

            time.sleep(self.delay)

        logger.info(f"Scraping finished. Total pages scraped: {len(self.scraped_content)}")
        return self.scraped_content

    def save_content(self, filepath: Optional[str] = None) -> str:
        """Saves the scraped content to a JSON file."""
        filepath = filepath or settings.scraped_data_file
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_content, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.scraped_content)} pages to {filepath}")
        return filepath

    def load_content(self, filepath: Optional[str] = None) -> List[Dict]:
        """Loads scraped content from a JSON file."""
        filepath = filepath or settings.scraped_data_file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.scraped_content = json.load(f)
            logger.info(f"Loaded {len(self.scraped_content)} pages from {filepath}")
            return self.scraped_content
        except FileNotFoundError:
            logger.warning(f"No existing content file found at {filepath}")
            return []


def main():
    """Main function to run the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stardew Valley Wiki Scraper (Rich Data Version)')
    parser.add_argument('--max-pages', type=int, default=1000, help='Maximum pages to scrape')
    parser.add_argument('--force', action='store_true', help='Force re-scraping')
    parser.add_argument('--output-file', type=str, default=settings.scraped_data_file)
    
    args = parser.parse_args()
    
    scraper = StardewWikiScraper(max_pages=args.max_pages)
    
    if not args.force and Path(args.output_file).exists():
        logger.info(f"Data file found. Use --force to re-scrape.")
        return
        
    scraper.scrape_website()
    scraper.save_content(filepath=args.output_file)
    
    logger.info("=" * 50)
    logger.info("SCRAPING SUMMARY")
    pages_with_images = sum(1 for p in scraper.scraped_content if p.get('image_url'))
    total_tables = sum(len(p.get('tables', [])) for p in scraper.scraped_content)
    logger.info(f"Total pages scraped: {len(scraper.scraped_content)}")
    logger.info(f"Pages with main image: {pages_with_images}")
    logger.info(f"Total tables extracted: {total_tables}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()