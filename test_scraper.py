#!/usr/bin/env python3
"""Test script to check if wiki scraping works for a single page."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.scraper.wiki_scraper import StardewWikiScraper

def test_single_page():
    """Test scraping a single page."""
    scraper = StardewWikiScraper()
    
    # Test with a known working page
    test_url = "https://stardewvalleywiki.com/Crops"
    print(f"Testing URL: {test_url}")
    
    content = scraper.get_page_content(test_url)
    
    if content:
        print(f"✅ Successfully scraped: {content['title']}")
        print(f"📄 Content length: {len(content['content'])} characters")
        print(f"📊 Tables found: {len(content['tables'])}")
        print(f"ℹ️ Infobox data: {len(content['infobox'])} items")
        return True
    else:
        print("❌ Failed to scrape content")
        return False

if __name__ == "__main__":
    test_single_page()
