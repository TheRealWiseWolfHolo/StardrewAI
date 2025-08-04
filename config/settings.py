"""Configuration management for the Stardew Valley AI agent."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", alias="OPENAI_MODEL")
    
    # Vector Database Configuration
    chroma_db_path: str = Field(default="./data/chroma_db", alias="CHROMA_DB_PATH")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    
    # Web Scraping Configuration
    wiki_base_url: str = Field(default="https://stardewvalleywiki.com", alias="WIKI_BASE_URL")
    scrape_delay: float = Field(default=1.0, alias="SCRAPE_DELAY")
    max_concurrent_requests: int = Field(default=5, alias="MAX_CONCURRENT_REQUESTS")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8002, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # Agent Configuration
    default_mode: str = Field(default="hints", alias="DEFAULT_MODE")
    max_response_length: int = Field(default=500, alias="MAX_RESPONSE_LENGTH")
    enable_spoiler_protection: bool = Field(default=True, alias="ENABLE_SPOILER_PROTECTION")
    
    # Data Storage
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    scraped_data_file: str = Field(default="./data/wiki_content.json", alias="SCRAPED_DATA_FILE")
    processed_data_file: str = Field(default="./data/processed_content.json", alias="PROCESSED_DATA_FILE")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }

# Global settings instance
settings = Settings()

# Ensure data directories exist
Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_db_path).parent.mkdir(parents=True, exist_ok=True)
