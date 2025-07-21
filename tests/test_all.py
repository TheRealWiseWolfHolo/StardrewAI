"""Test suite for the Stardew Valley AI assistant."""

import json
import pytest
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestConfiguration:
    """Test configuration and settings."""
    
    def test_settings_import(self):
        """Test that settings can be imported."""
        try:
            from config.settings import settings
            assert settings is not None
        except ImportError:
            pytest.skip("Configuration not available - dependencies not installed")
    
    def test_environment_variables(self):
        """Test environment variable loading."""
        try:
            from config.settings import settings
            # Should have default values even without .env
            assert settings.wiki_base_url == "https://stardewvalleywiki.com"
            assert settings.default_mode == "hints"
        except ImportError:
            pytest.skip("Configuration not available - dependencies not installed")


class TestWikiScraper:
    """Test wiki scraping functionality."""
    
    def test_scraper_import(self):
        """Test that scraper can be imported."""
        try:
            from src.scraper.wiki_scraper import StardewWikiScraper
            scraper = StardewWikiScraper()
            assert scraper is not None
            assert scraper.base_url == "https://stardewvalleywiki.com"
        except ImportError:
            pytest.skip("Scraper not available - dependencies not installed")
    
    def test_content_splitting(self):
        """Test content splitting functionality."""
        try:
            from src.scraper.wiki_scraper import StardewWikiScraper
            scraper = StardewWikiScraper()
            
            # Test content splitting
            test_content = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
            chunks = scraper._split_content(test_content, max_chunk_size=20)
            assert len(chunks) > 1
        except ImportError:
            pytest.skip("Scraper not available - dependencies not installed")


class TestRAGSystem:
    """Test RAG system functionality."""
    
    def test_rag_import(self):
        """Test that RAG system can be imported."""
        try:
            from src.rag.knowledge_base import StardewRAGSystem
            # Don't initialize to avoid ChromaDB dependency
            assert StardewRAGSystem is not None
        except ImportError:
            pytest.skip("RAG system not available - dependencies not installed")
    
    def test_content_processing(self):
        """Test content processing functionality."""
        try:
            from src.rag.knowledge_base import StardewRAGSystem
            rag = StardewRAGSystem()
            
            # Test data processing
            test_data = [{
                'title': 'Test Page',
                'url': 'http://test.com',
                'content': 'This is test content for processing.',
                'tables': [],
                'infobox': {}
            }]
            
            processed = rag.process_scraped_data(test_data)
            assert len(processed) >= 1
            assert processed[0]['title'] == 'Test Page'
            
        except ImportError:
            pytest.skip("RAG system not available - dependencies not installed")


class TestAgent:
    """Test agent functionality."""
    
    def test_agent_import(self):
        """Test that agent can be imported."""
        try:
            from src.agent.stardew_agent import AgentMode, StardewAgent
            assert AgentMode.HINTS.value == "hints"
            assert AgentMode.WALKTHROUGH.value == "walkthrough"
        except ImportError:
            pytest.skip("Agent not available - dependencies not installed")
    
    def test_agent_modes(self):
        """Test agent mode functionality."""
        try:
            from src.agent.stardew_agent import AgentMode
            
            # Test enum values
            assert AgentMode.HINTS.value == "hints"
            assert AgentMode.WALKTHROUGH.value == "walkthrough"
            
            # Test that we can create mode from string
            mode_from_string = AgentMode("hints")
            assert mode_from_string == AgentMode.HINTS
            
        except ImportError:
            pytest.skip("Agent not available - dependencies not installed")


class TestAPI:
    """Test API functionality."""
    
    def test_api_import(self):
        """Test that API can be imported."""
        try:
            from src.api.main import app
            assert app is not None
            assert app.title == "Stardew Valley AI Assistant"
        except ImportError:
            pytest.skip("API not available - dependencies not installed")


def test_project_structure():
    """Test that the project structure is correct."""
    project_root = Path(__file__).parent.parent
    
    # Check main directories
    assert (project_root / "src").exists()
    assert (project_root / "src" / "scraper").exists()
    assert (project_root / "src" / "rag").exists()
    assert (project_root / "src" / "agent").exists()
    assert (project_root / "src" / "api").exists()
    assert (project_root / "src" / "frontend").exists()
    assert (project_root / "config").exists()
    
    # Check key files
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / ".env.example").exists()
    assert (project_root / "setup.py").exists()


def test_requirements_file():
    """Test that requirements.txt contains expected packages."""
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements.txt"
    
    assert requirements_file.exists()
    
    content = requirements_file.read_text()
    
    # Check for key dependencies
    assert "langchain" in content
    assert "fastapi" in content
    assert "chromadb" in content
    assert "beautifulsoup4" in content
    assert "openai" in content


if __name__ == "__main__":
    # Run tests
    print("Running Stardew Valley AI Tests...")
    print("=" * 50)
    
    # Run pytest
    exit_code = pytest.main([__file__, "-v"])
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(exit_code)
