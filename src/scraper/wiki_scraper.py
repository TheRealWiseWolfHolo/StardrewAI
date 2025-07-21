"""Web scraper for Stardew Valley Wiki content."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Import settings with proper path handling
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.settings import settings
except ImportError:
    # Fallback settings if config module not available
    class Settings:
        wiki_base_url = "https://stardewvalleywiki.com"
        scrape_delay = 1.0
        max_concurrent_requests = 5
        scraped_data_file = "./data/wiki_content.json"
    
    settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StardewWikiScraper:
    """Scrapes content from the Stardew Valley Wiki with enhanced discovery."""
    
    def __init__(self, max_pages: int = 200):
        self.base_url = settings.wiki_base_url
        self.delay = settings.scrape_delay
        self.max_concurrent = settings.max_concurrent_requests
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.scraped_content: List[Dict] = []
        
        # Comprehensive list of key wiki pages (175+ pages)
        self.key_pages = [
            # Main pages
            "/Stardew_Valley_Wiki",
            
            # Core gameplay
            "/Crops", "/Animals", "/Mining", "/Fishing", "/Foraging", "/Cooking", "/Crafting",
            "/Combat", "/Energy", "/Health", "/Skills", "/Experience", "/Professions",
            
            # Social
            "/Marriage", "/Friendship", "/Villagers", "/Bachelor", "/Bachelorette",
            "/Abigail", "/Alex", "/Elliott", "/Emily", "/Haley", "/Harvey", "/Leah", 
            "/Maru", "/Penny", "/Sam", "/Sebastian", "/Shane",
            "/Caroline", "/Clint", "/Demetrius", "/Dwarf", "/Evelyn", "/George", 
            "/Gus", "/Jas", "/Jodi", "/Kent", "/Lewis", "/Linus", "/Marnie", 
            "/Pam", "/Pierre", "/Robin", "/Vincent", "/Willy", "/Wizard",
            
            # Locations
            "/Pelican_Town", "/The_Beach", "/The_Desert", "/The_Forest", "/The_Mountain",
            "/Cindersap_Forest", "/The_Mines", "/Skull_Cavern", "/Secret_Woods",
            "/Ginger_Island", "/Volcano_Dungeon", "/Island_West", "/Island_North",
            "/Island_South", "/Island_East", "/Fern_Islands",
            
            # Farm & Buildings
            "/Farm", "/Farmhouse", "/Farm_Buildings", "/Coop", "/Barn", "/Stable",
            "/Silo", "/Well", "/Mayonnaise_Machine", "/Cheese_Press", "/Keg",
            "/Preserves_Jar", "/Oil_Maker", "/Loom", "/Bee_House", "/Lightning_Rod",
            "/Slime_Hutch", "/Fish_Pond", "/Shed", "/Cabin", "/Greenhouse",
            "/Junimo_Hut", "/Gold_Clock", "/Obelisk",
            
            # Items & Resources
            "/Seeds", "/Fertilizer", "/Tools", "/Weapons", "/Rings", "/Boots",
            "/Food", "/Artisan_Goods", "/Animal_Products", "/Fish", "/Gems",
            "/Minerals", "/Artifacts", "/Resources", "/Materials", "/Trash",
            "/Loved_Gifts", "/Liked_Gifts", "/Neutral_Gifts", "/Disliked_Gifts", "/Hated_Gifts",
            
            # Quests & Events
            "/Quests", "/Community_Center", "/Bundles", "/JojaMart", "/Achievements",
            "/Heart_Events", "/Cutscenes", "/Festivals", "/Calendar",
            "/Egg_Festival", "/Flower_Dance", "/Luau", "/Dance_of_the_Moonlight_Jellies",
            "/Stardew_Valley_Fair", "/Spirit's_Eve", "/Festival_of_Ice", "/Feast_of_the_Winter_Star",
            
            # Game mechanics
            "/Weather", "/Seasons", "/Time", "/Sleep", "/Shipping", "/Money",
            "/Luck", "/Museum", "/Library", "/Traveling_Cart", "/Night_Market",
            
            # Advanced content
            "/Perfection", "/Professor_Snail", "/Gourmand_Frog", "/Simon_Says", 
            "/Crystal_Cave", "/Qi_Challenges", "/Walnut_Room", "/Golden_Walnuts", 
            "/Parrot_Express", "/Island_Obelisk",
            
            # Special items
            "/Prismatic_Shard", "/Ancient_Fruit", "/Sweet_Gem_Berry", "/Starfruit",
            "/Coffee", "/Wine", "/Pale_Ale", "/Mead", "/Truffle_Oil", "/Cheese",
            "/Mayonnaise", "/Cloth", "/Honey", "/Jelly", "/Pickle", "/Juice",
            
            # All individual crops
            "/Parsnip", "/Green_Bean", "/Cauliflower", "/Potato", "/Tulip_Bulb", "/Kale", "/Jazz",
            "/Garlic", "/Blue_Jazz", "/Tulip", "/Parsnip_Seeds", "/Bean_Starter", "/Cauliflower_Seeds",
            "/Potato_Seeds", "/Kale_Seeds", "/Tulip_Bulb", "/Jazz_Seeds", "/Garlic_Seeds",
            "/Melon", "/Tomato", "/Hot_Pepper", "/Blueberry", "/Radish", "/Wheat", "/Hops",
            "/Spice_Berry", "/Summer_Spangle", "/Poppy", "/Summer_Seeds", "/Tomato_Seeds",
            "/Pepper_Seeds", "/Blueberry_Seeds", "/Radish_Seeds", "/Wheat_Seeds", "/Hops_Starter",
            "/Eggplant", "/Corn", "/Pumpkin", "/Bok_Choy", "/Yam", "/Beet", "/Amaranth",
            "/Grape", "/Sweet_Gem_Berry", "/Cranberries", "/Sunflower", "/Fairy_Rose",
            "/Eggplant_Seeds", "/Corn_Seeds", "/Pumpkin_Seeds", "/Bok_Choy_Seeds", "/Yam_Seeds",
            "/Beet_Seeds", "/Amaranth_Seeds", "/Grape_Starter", "/Cranberry_Seeds", "/Sunflower_Seeds",
            
            # All fish types
            "/Anchovy", "/Tuna", "/Sardine", "/Bream", "/Largemouth_Bass", "/Smallmouth_Bass",
            "/Rainbow_Trout", "/Salmon", "/Walleye", "/Perch", "/Carp", "/Catfish", "/Pike",
            "/Sunfish", "/Red_Mullet", "/Herring", "/Eel", "/Octopus", "/Red_Snapper", "/Squid",
            "/Sea_Cucumber", "/Super_Cucumber", "/Ghostfish", "/Stonefish", "/Ice_Pip", "/Lava_Eel",
            "/Sandfish", "/Scorpion_Carp", "/Flounder", "/Midnight_Carp", "/Mutant_Carp", "/Sturgeon",
            "/Tiger_Trout", "/Bullhead", "/Tilapia", "/Chub", "/Dorado", "/Albacore", "/Shad",
            "/Lingcod", "/Halibut", "/Woodskip", "/Void_Salmon", "/Slimejack", "/Midnight_Squid",
            "/Spook_Fish", "/Blobfish", "/Crimsonfish", "/Angler", "/Legend", "/Glacierfish", "/Mutant_Carp",
            
            # All animals
            "/Chicken", "/Duck", "/Rabbit", "/Cow", "/Goat", "/Sheep", "/Pig", "/Dinosaur",
            "/Blue_Chicken", "/Void_Chicken", "/Golden_Chicken", "/Ostrich",
            
            # All minerals/gems
            "/Quartz", "/Earth_Crystal", "/Frozen_Tear", "/Fire_Quartz", "/Emerald", "/Aquamarine",
            "/Ruby", "/Amethyst", "/Topaz", "/Jade", "/Diamond", "/Iridium_Ore", "/Gold_Ore",
            "/Iron_Ore", "/Copper_Ore", "/Coal", "/Stone", "/Clay", "/Battery_Pack",
            
            # Modding and technical
            "/Modding", "/Save_File", "/Options", "/Controls", "/Updates", "/Mobile", "/Console"
        ]
        
        # Categories for discovery
        self.category_pages = [
            "/Category:Crops", "/Category:Fish", "/Category:Minerals", "/Category:Cooking",
            "/Category:Villagers", "/Category:Locations", "/Category:Buildings"
        ]

    def get_page_content(self, url: str) -> Optional[Dict]:
        """Scrape content from a single page."""
        try:
            if url in self.visited_urls:
                return None
                
            logger.info(f"Scraping: {url}")
            self.visited_urls.add(url)
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            if response.url != url:
                logger.info(f"Redirected to: {response.url}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('h1', {'class': 'firstHeading'})
            title_text = title.get_text().strip() if title else "Unknown"
            
            # Remove navigation elements
            for element in soup.find_all(['nav', 'aside', 'footer', 'script', 'style']):
                element.decompose()
            
            # Extract main content
            content_div = soup.find('div', {'id': 'mw-content-text'})
            if not content_div:
                content_div = soup.find('div', {'class': 'mw-parser-output'})
            
            if content_div:
                # Clean up edit links
                for element in content_div.find_all(['span'], {'class': 'mw-editsection'}):
                    element.decompose()
                
                text_content = content_div.get_text(strip=True, separator='\n')
                
                # Extract tables
                tables = []
                for table in content_div.find_all('table'):
                    table_data = self._extract_table_data(table)
                    if table_data:
                        tables.append(table_data)
                
                # Extract infobox
                infobox = content_div.find('table', {'class': 'infobox'})
                infobox_data = self._extract_infobox_data(infobox) if infobox else {}
                
                return {
                    'url': url,
                    'title': title_text,
                    'content': text_content,
                    'tables': tables,
                    'infobox': infobox_data,
                    'scraped_at': time.time()
                }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None

    def discover_wiki_links(self, content_div) -> Set[str]:
        """Discover additional wiki links."""
        links = set()
        try:
            if content_div:
                for link in content_div.find_all('a', href=True):
                    href = link.get('href', '')
                    if href.startswith('/') and not href.startswith('//'):
                        if not any(skip in href for skip in [
                            'Category:', 'File:', 'Template:', 'Help:', 'Special:',
                            'Talk:', 'User:', '#', '?', '&action=', 'index.php'
                        ]):
                            url = href.split('#')[0].split('?')[0]
                            if url and len(url) > 1:
                                links.add(url)
        except Exception as e:
            logger.warning(f"Error discovering links: {str(e)}")
        return links

    def get_category_pages(self, category_url: str) -> Set[str]:
        """Get pages from a category."""
        pages = set()
        try:
            logger.info(f"Exploring category: {category_url}")
            url = urljoin(self.base_url, category_url)
            content = self.get_page_content(url)
            
            if content:
                soup = BeautifulSoup(content['content'], 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if href.startswith('/') and not href.startswith('//'):
                        if not any(skip in href for skip in [
                            'Category:', 'File:', 'Template:', 'Help:', 'Special:',
                            'Talk:', 'User:', '#', '?', '&action='
                        ]):
                            pages.add(href.split('#')[0].split('?')[0])
        except Exception as e:
            logger.warning(f"Error exploring category {category_url}: {str(e)}")
        return pages

    def discover_all_pages(self) -> Set[str]:
        """Discover all relevant pages."""
        all_pages = set(self.key_pages)
        
        logger.info("Exploring categories for additional pages...")
        for category in self.category_pages:
            if len(all_pages) >= self.max_pages:
                break
            category_pages = self.get_category_pages(category)
            all_pages.update(category_pages)
            time.sleep(self.delay)
        
        logger.info("Discovering links from key pages...")
        discovery_pages = list(all_pages)[:20]  # Limit to avoid infinite crawling
        
        for page_path in discovery_pages:
            if len(all_pages) >= self.max_pages:
                break
                
            url = urljoin(self.base_url, page_path)
            if url not in self.visited_urls:
                content = self.get_page_content(url)
                if content:
                    soup = BeautifulSoup(content['content'], 'html.parser')
                    content_div = soup.find('div', {'id': 'mw-content-text'})
                    if not content_div:
                        content_div = soup.find('div', {'class': 'mw-parser-output'})
                    
                    if content_div:
                        discovered_links = self.discover_wiki_links(content_div)
                        all_pages.update(discovered_links)
                
                time.sleep(self.delay)
        
        filtered_pages = self.filter_relevant_pages(all_pages)
        logger.info(f"Discovered {len(filtered_pages)} relevant pages to scrape")
        return filtered_pages

    def filter_relevant_pages(self, pages: Set[str]) -> Set[str]:
        """Filter pages for game relevance."""
        relevant_pages = set()
        
        priority_keywords = [
            'crop', 'animal', 'fish', 'mineral', 'gem', 'artifact', 'villager', 
            'marriage', 'heart', 'event', 'festival', 'quest', 'bundle', 'skill',
            'mine', 'desert', 'island', 'cave', 'forest', 'beach', 'mountain',
            'building', 'machine', 'tool', 'weapon', 'ring', 'boot', 'hat',
            'food', 'recipe', 'cooking', 'craft', 'artisan', 'seed', 'fruit',
            'vegetable', 'flower', 'tree', 'season', 'weather', 'calendar',
            'community', 'center', 'joja', 'achievement', 'perfection', 'golden',
            'prismatic', 'ancient', 'rare', 'legendary', 'statue', 'obelisk'
        ]
        
        # Always include key pages
        relevant_pages.update(self.key_pages)
        
        for page in pages:
            if len(relevant_pages) >= self.max_pages:
                break
                
            page_lower = page.lower()
            if any(keyword in page_lower for keyword in priority_keywords):
                relevant_pages.add(page)
        
        return relevant_pages

    def _extract_table_data(self, table) -> Optional[Dict]:
        """Extract table data."""
        try:
            headers = []
            rows = []
            
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text().strip())
            
            for row in table.find_all('tr')[1:]:
                row_data = []
                for cell in row.find_all(['td', 'th']):
                    row_data.append(cell.get_text().strip())
                if row_data:
                    rows.append(row_data)
            
            if headers and rows:
                return {'headers': headers, 'rows': rows}
        except Exception as e:
            logger.warning(f"Error extracting table: {str(e)}")
        return None

    def _extract_infobox_data(self, infobox) -> Dict:
        """Extract infobox data."""
        data = {}
        try:
            if infobox:
                for row in infobox.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip()
                        value = cells[1].get_text().strip()
                        if key and value:
                            data[key] = value
        except Exception as e:
            logger.warning(f"Error extracting infobox: {str(e)}")
        return data

    def scrape_all_pages(self, discover_mode: bool = True) -> List[Dict]:
        """Scrape all pages with optional discovery."""
        if discover_mode:
            logger.info("Discovery mode enabled - finding all relevant pages...")
            pages_to_scrape = self.discover_all_pages()
        else:
            logger.info("Using predefined page list only...")
            pages_to_scrape = set(self.key_pages)
        
        pages_list = list(pages_to_scrape)[:self.max_pages]
        logger.info(f"Starting to scrape {len(pages_list)} pages")
        
        successful_scrapes = 0
        failed_scrapes = 0
        
        for i, page_path in enumerate(pages_list, 1):
            url = urljoin(self.base_url, page_path)
            
            logger.info(f"[{i}/{len(pages_list)}] Scraping: {page_path}")
            content = self.get_page_content(url)
            
            if content:
                self.scraped_content.append(content)
                successful_scrapes += 1
                logger.info(f"✓ Success: {content['title']} ({len(content['content'])} chars)")
            else:
                failed_scrapes += 1
                logger.warning(f"✗ Failed: {page_path}")
            
            time.sleep(self.delay)
            
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(pages_list)} ({successful_scrapes} successful)")
        
        logger.info(f"Scraping completed! {len(self.scraped_content)} pages scraped")
        if successful_scrapes + failed_scrapes > 0:
            success_rate = 100 * successful_scrapes / (successful_scrapes + failed_scrapes)
            logger.info(f"Success rate: {success_rate:.1f}%")
        return self.scraped_content

    def save_content(self, filepath: Optional[str] = None) -> str:
        """Save scraped content."""
        if not filepath:
            filepath = settings.scraped_data_file
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_content, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.scraped_content)} pages to {filepath}")
        return filepath

    def load_content(self, filepath: Optional[str] = None) -> List[Dict]:
        """Load previously scraped content."""
        if not filepath:
            filepath = settings.scraped_data_file
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.scraped_content = json.load(f)
            logger.info(f"Loaded {len(self.scraped_content)} pages from {filepath}")
            return self.scraped_content
        except FileNotFoundError:
            logger.warning(f"No existing content file found at {filepath}")
            return []


def main():
    """Enhanced scraper main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Stardew Valley Wiki Scraper')
    parser.add_argument('--max-pages', type=int, default=200, 
                       help='Maximum pages to scrape (default: 200)')
    parser.add_argument('--no-discovery', action='store_true',
                       help='Disable automatic page discovery')
    parser.add_argument('--force', action='store_true',
                       help='Force re-scraping')
    
    args = parser.parse_args()
    
    scraper = StardewWikiScraper(max_pages=args.max_pages)
    
    if not args.force:
        existing_content = scraper.load_content()
        if existing_content:
            logger.info(f"Found {len(existing_content)} existing pages. Use --force to re-scrape.")
            return
    
    discovery_mode = not args.no_discovery
    scraper.scrape_all_pages(discover_mode=discovery_mode)
    scraper.save_content()
    
    # Summary
    total_chars = sum(len(content.get('content', '')) for content in scraper.scraped_content)
    total_tables = sum(len(content.get('tables', [])) for content in scraper.scraped_content)
    
    logger.info("=" * 50)
    logger.info("ENHANCED SCRAPING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total pages scraped: {len(scraper.scraped_content)}")
    logger.info(f"Total content size: {total_chars:,} characters")
    logger.info(f"Total tables extracted: {total_tables}")
    if len(scraper.scraped_content) > 0:
        logger.info(f"Average page size: {total_chars // len(scraper.scraped_content):,} characters")
    
    logger.info("Sample of scraped pages:")
    for i, content in enumerate(scraper.scraped_content[:10]):
        logger.info(f"  {i+1}. {content['title']} ({len(content['content'])} chars)")
    
    if len(scraper.scraped_content) > 10:
        logger.info(f"  ... and {len(scraper.scraped_content) - 10} more pages")
    
    logger.info("Enhanced scraping completed successfully!")


if __name__ == "__main__":
    main()
