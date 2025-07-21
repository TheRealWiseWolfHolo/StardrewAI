#!/usr/bin/env python3
"""Test script for the enhanced Stardew Valley Wiki scraper."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.wiki_scraper import StardewWikiScraper

def test_discovery():
    """Test the page discovery functionality."""
    print("🔍 Testing enhanced Stardew Valley Wiki scraper...")
    print("=" * 60)
    
    # Create scraper with small limit for testing
    scraper = StardewWikiScraper(max_pages=50)
    
    print(f"📚 Base key pages: {len(scraper.key_pages)}")
    print(f"📁 Category pages to explore: {len(scraper.category_pages)}")
    print()
    
    # Test discovery without full scraping
    print("🔎 Discovering pages...")
    try:
        discovered_pages = scraper.discover_all_pages()
        print(f"✅ Discovered {len(discovered_pages)} total pages")
        
        # Show sample of discovered pages
        print("\n📄 Sample of discovered pages:")
        for i, page in enumerate(list(discovered_pages)[:20]):
            print(f"  {i+1:2d}. {page}")
        
        if len(discovered_pages) > 20:
            print(f"  ... and {len(discovered_pages) - 20} more pages")
            
        return True
        
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        return False

def test_quick_scrape():
    """Test scraping a few pages to validate functionality."""
    print("\n" + "=" * 60)
    print("🚀 Testing quick scrape of 5 pages...")
    
    scraper = StardewWikiScraper(max_pages=5)
    
    try:
        # Scrape without discovery for speed
        content = scraper.scrape_all_pages(discover_mode=False)
        
        if content:
            print(f"✅ Successfully scraped {len(content)} pages")
            
            # Show details of scraped content
            total_chars = sum(len(c.get('content', '')) for c in content)
            total_tables = sum(len(c.get('tables', [])) for c in content)
            
            print(f"📊 Total content: {total_chars:,} characters")
            print(f"📋 Total tables: {total_tables}")
            
            print("\n📄 Scraped pages:")
            for i, c in enumerate(content):
                print(f"  {i+1}. {c['title']} ({len(c['content']):,} chars, {len(c.get('tables', []))} tables)")
            
            return True
        else:
            print("❌ No content was scraped")
            return False
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎮 Enhanced Stardew Valley Wiki Scraper Test")
    print("=" * 60)
    
    # Test discovery
    discovery_success = test_discovery()
    
    # Test scraping
    scrape_success = test_quick_scrape()
    
    print("\n" + "=" * 60)
    print("📈 TEST RESULTS")
    print("=" * 60)
    print(f"Discovery test: {'✅ PASSED' if discovery_success else '❌ FAILED'}")
    print(f"Scraping test:  {'✅ PASSED' if scrape_success else '❌ FAILED'}")
    
    if discovery_success and scrape_success:
        print("\n🎉 All tests passed! Your enhanced scraper is ready.")
        print("\nTo run full scraping with discovery:")
        print("  python src/scraper/wiki_scraper.py --max-pages 200")
        print("\nTo run without discovery (faster):")
        print("  python src/scraper/wiki_scraper.py --no-discovery")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
