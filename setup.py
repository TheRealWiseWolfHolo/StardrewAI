#!/usr/bin/env python3
"""Setup script for the Stardew Valley AI assistant."""

import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def setup_environment():
    """Set up the environment and check requirements."""
    print("🌱 Setting up Stardew Valley AI Assistant...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📋 Please copy .env.example to .env and configure your settings:")
        print("   cp .env.example .env")
        print("   # Then edit .env with your OpenAI API key")
        return False
    
    # Check if OpenAI API key is set
    if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
        print("❌ OpenAI API key not configured!")
        print("📋 Please set your OpenAI API key in the .env file:")
        print("   OPENAI_API_KEY=your-actual-api-key")
        return False
    
    # Create necessary directories
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Data directory created: {data_dir}")
    
    chroma_dir = Path(settings.chroma_db_path).parent
    chroma_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ ChromaDB directory created: {chroma_dir}")
    
    return True


def scrape_wiki():
    """Scrape the Stardew Valley wiki."""
    print("🕷️  Scraping Stardew Valley Wiki...")
    
    try:
        from src.scraper.wiki_scraper import StardewWikiScraper
        
        scraper = StardewWikiScraper()
        
        # Check if data already exists
        if Path(settings.scraped_data_file).exists():
            print("📄 Existing scraped data found.")
            response = input("Do you want to re-scrape? (y/N): ")
            if response.lower() != 'y':
                print("✅ Using existing scraped data")
                return True
        
        # Scrape the wiki
        content = scraper.scrape_all_pages()
        if content:
            scraper.save_content()
            print(f"✅ Successfully scraped {len(content)} pages")
            return True
        else:
            print("❌ Failed to scrape wiki content")
            return False
            
    except ImportError as e:
        print(f"❌ Import error during scraping: {str(e)}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        return False


def build_knowledge_base():
    """Build the vector database from scraped content."""
    print("🧠 Building knowledge base...")
    
    try:
        from src.rag.knowledge_base import StardewRAGSystem
        
        rag_system = StardewRAGSystem()
        
        # Check if database already exists
        try:
            count = rag_system.collection.count()
            if count > 0:
                print(f"📚 Existing database found with {count} documents.")
                response = input("Do you want to rebuild? (y/N): ")
                if response.lower() != 'y':
                    print("✅ Using existing knowledge base")
                    return True
                rag_system.reset_database()
        except Exception as e:
            # Database doesn't exist or is empty - this is expected for first run
            print("📚 Creating new knowledge base...")
        
        # Build the database
        chunks_added = rag_system.build_vector_database()
        if chunks_added > 0:
            print(f"✅ Successfully built knowledge base with {chunks_added} chunks")
            return True
        else:
            print("❌ Failed to build knowledge base")
            return False
            
    except ImportError as e:
        print(f"❌ Import error building knowledge base: {str(e)}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error building knowledge base: {str(e)}")
        return False


def test_agent():
    """Test the agent functionality."""
    print("🤖 Testing agent...")
    
    try:
        from src.agent.stardew_agent import StardewAgent, AgentMode
        
        # Test hints mode
        print("Testing Hints Mode...")
        agent = StardewAgent(mode=AgentMode.HINTS)
        response = agent.chat("How do I start farming?")
        print(f"✅ Hints mode response: {response['text'][:100]}...")
        
        # Test walkthrough mode
        print("Testing Walkthrough Mode...")
        agent.set_mode(AgentMode.WALKTHROUGH)
        response = agent.chat("How do I start farming?")
        print(f"✅ Walkthrough mode response: {response['text'][:100]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error testing agent: {str(e)}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error testing agent: {str(e)}")
        return False


def start_server():
    """Start the web server."""
    print("🚀 Starting web server...")
    
    try:
        import uvicorn
        from src.api.main import app
        
        print(f"🌐 Server will be available at: http://{settings.api_host}:{settings.api_port}")
        print("✅ Starting server... (Press Ctrl+C to stop)")
        
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except ImportError as e:
        print(f"❌ Import error starting server: {str(e)}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Setup and run Stardew Valley AI Assistant")
    parser.add_argument("--setup-only", action="store_true", help="Only run setup, don't start server")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip wiki scraping")
    parser.add_argument("--skip-kb", action="store_true", help="Skip knowledge base building")
    parser.add_argument("--skip-test", action="store_true", help="Skip agent testing")
    
    args = parser.parse_args()
    
    print("🌟 Stardew Valley AI Assistant Setup")
    print("=" * 50)
    
    # Setup environment
    if not setup_environment():
        print("\n❌ Setup failed. Please fix the issues above and try again.")
        return
    
    # Scrape wiki
    if not args.skip_scrape:
        if not scrape_wiki():
            print("\n❌ Wiki scraping failed.")
            return
    
    # Build knowledge base
    if not args.skip_kb:
        if not build_knowledge_base():
            print("\n❌ Knowledge base building failed.")
            return
    
    # Test agent
    if not args.skip_test:
        if not test_agent():
            print("\n❌ Agent testing failed.")
            return
    
    print("\n✅ Setup completed successfully!")
    
    if not args.setup_only:
        print("\n" + "=" * 50)
        start_server()
    else:
        print("\n🚀 To start the server, run:")
        print(f"   uvicorn src.api.main:app --host {settings.api_host} --port {settings.api_port} --reload")


if __name__ == "__main__":
    main()
