# Stardew Valley AI Assistant - Developer Guide

## Project Overview

The Stardew Valley AI Assistant is a sophisticated RAG (Retrieval-Augmented Generation) system that helps players navigate the game with two distinct modes:

1. **Hints Mode**: Provides subtle guidance without spoilers
2. **Walkthrough Mode**: Offers detailed step-by-step instructions

## Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │ ─→ │   FastAPI API   │ ─→ │  LangChain      │
│   (HTML/JS)     │    │   (REST API)    │    │  Agent          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │  RAG System     │
                                               │  (ChromaDB)     │
                                               └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │  Wiki Scraper   │
                                               │  (BeautifulSoup)│
                                               └─────────────────┘
```

### Data Flow

1. **Wiki Scraping**: BeautifulSoup scrapes Stardew Valley Wiki pages
2. **Content Processing**: Text is chunked and processed for vector storage
3. **Vector Database**: ChromaDB stores embeddings using sentence-transformers
4. **Agent Processing**: LangChain agent retrieves relevant context and generates responses
5. **Web Interface**: FastAPI serves responses to the React-like frontend

## Installation & Setup

### Prerequisites

- Python 3.8+
- OpenAI API key
- Internet connection for wiki scraping

### Quick Start

1. **Clone and Navigate**:
   ```bash
   cd StardrewAI
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. **Run Setup Script**:
   ```bash
   python setup.py
   ```

This will:
- Scrape the wiki (takes 5-10 minutes)
- Build the vector database
- Test the agent
- Start the web server at `http://localhost:8000`

### Manual Setup

If you prefer to run each step manually:

```bash
# 1. Scrape wiki data
python -m src.scraper.wiki_scraper

# 2. Build knowledge base
python -m src.rag.knowledge_base

# 3. Test the agent
python -m src.agent.stardew_agent

# 4. Start the web server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | GPT model to use | `gpt-3.5-turbo` |
| `CHROMA_DB_PATH` | Vector database path | `./data/chroma_db` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `API_HOST` | Web server host | `0.0.0.0` |
| `API_PORT` | Web server port | `8000` |
| `DEBUG` | Enable debug mode | `True` |

### Agent Configuration

The agent behavior can be customized through settings:

- **Response Length**: Controls max tokens in responses
- **Spoiler Protection**: Prevents revealing late-game content in hints mode
- **Mode Switching**: Allows dynamic switching between modes

## API Endpoints

### Core Endpoints

- `GET /` - Web interface
- `POST /api/chat` - Send chat message
- `POST /api/mode` - Change agent mode
- `GET /api/status` - Get agent status
- `GET /api/history` - Get conversation history
- `POST /api/clear` - Clear conversation
- `GET /api/modes` - Get available modes

### Example API Usage

```python
import requests

# Send a chat message
response = requests.post('http://localhost:8000/api/chat', json={
    'message': 'How do I grow crops?',
    'mode': 'hints'
})

print(response.json()['response'])
```

## Development

### Project Structure

```
StardrewAI/
├── src/
│   ├── scraper/          # Wiki scraping
│   │   ├── __init__.py
│   │   └── wiki_scraper.py
│   ├── rag/              # RAG system
│   │   ├── __init__.py
│   │   └── knowledge_base.py
│   ├── agent/            # LangChain agent
│   │   ├── __init__.py
│   │   └── stardew_agent.py
│   ├── api/              # FastAPI backend
│   │   ├── __init__.py
│   │   └── main.py
│   └── frontend/         # Web interface
│       └── templates/
├── config/               # Configuration
├── data/                 # Data storage
├── tests/                # Test suite
├── requirements.txt      # Dependencies
├── setup.py             # Setup script
└── .env.example         # Environment template
```

### Key Components

#### 1. Wiki Scraper (`src/scraper/wiki_scraper.py`)

Scrapes key Stardew Valley wiki pages:
- Crops, Animals, Mining, Fishing
- Characters, Locations, Quests
- Items, Crafting, Cooking

Features:
- Rate limiting to respect the server
- Table extraction for structured data
- Infobox processing for key-value pairs
- Error handling and retry logic

#### 2. RAG System (`src/rag/knowledge_base.py`)

Manages the knowledge base:
- Chunks content into manageable sizes
- Generates embeddings using sentence-transformers
- Stores in ChromaDB for similarity search
- Provides context retrieval for queries

#### 3. LangChain Agent (`src/agent/stardew_agent.py`)

Two-mode AI agent:

**Hints Mode**:
- Provides subtle guidance
- Avoids spoilers
- Encourages exploration
- Shorter responses (~200 words)

**Walkthrough Mode**:
- Detailed step-by-step instructions
- Complete information
- Comprehensive solutions
- Longer responses (no limit)

#### 4. FastAPI Backend (`src/api/main.py`)

RESTful API with:
- CORS support for web frontend
- Conversation memory management
- Mode switching capabilities
- Error handling and validation

#### 5. Web Frontend (`src/frontend/templates/`)

Modern web interface:
- Responsive design with Bootstrap
- Markdown support for rich text
- Real-time mode switching
- Conversation history
- Typing indicators

### Testing

Run the test suite:

```bash
# Run all tests
python tests/test_all.py

# Or with pytest
pytest tests/ -v
```

### Code Quality

Format code:
```bash
black src/
```

Lint code:
```bash
ruff check src/
```

## Customization

### Adding New Wiki Pages

Edit `src/scraper/wiki_scraper.py` and add URLs to the `key_pages` list:

```python
self.key_pages = [
    "/wiki/Your_New_Page",
    # ... existing pages
]
```

### Modifying Agent Behavior

Edit the prompts in `src/agent/stardew_agent.py`:

```python
system_message = """Your custom prompt here..."""
```

### Changing Response Modes

Add new modes to the `AgentMode` enum:

```python
class AgentMode(Enum):
    HINTS = "hints"
    WALKTHROUGH = "walkthrough"
    CUSTOM = "custom"  # Your new mode
```

### Frontend Customization

Modify `src/frontend/templates/index.html` for UI changes:
- Styling in the `<style>` section
- Functionality in the `<script>` section
- Layout in the HTML body

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **OpenAI API Errors**: Check your API key and usage limits

3. **ChromaDB Issues**: Delete the database directory and rebuild:
   ```bash
   rm -rf data/chroma_db
   python -m src.rag.knowledge_base
   ```

4. **Wiki Scraping Failures**: Check internet connection and reduce `max_concurrent_requests`

5. **Memory Issues**: Reduce chunk size in the RAG system

### Debug Mode

Enable debug logging in your `.env`:
```
DEBUG=True
```

This provides verbose output for troubleshooting.

### Performance Optimization

1. **Use faster embedding models** (trade-off with quality)
2. **Increase chunk sizes** for fewer database entries
3. **Implement caching** for repeated queries
4. **Use GPT-4** for better responses (higher cost)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- Use Black for formatting
- Follow PEP 8 conventions
- Add type hints
- Include docstrings
- Write tests for new features

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check this documentation
2. Review the test suite for examples
3. Open an issue on GitHub
4. Check OpenAI API documentation for LLM issues
