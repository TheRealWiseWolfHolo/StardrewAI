# Stardew Valley AI Chat Agent

An intelligent assistant that helps players navigate and master Stardew Valley using RAG (Retrieval-Augmented Generation) technology.

## Features

- 🎮 **Two Game Modes**:
  - **Hints Mode**: Provides subtle guidance without spoilers
  - **Full Walkthrough Mode**: Detailed step-by-step instructions

- 🔍 **Smart Knowledge Base**: 
  - Web-scraped Stardew Valley Wiki content
  - Vector-based semantic search
  - Up-to-date game information

- 🤖 **AI-Powered Chat**:
  - Context-aware responses using LangChain
  - Natural language understanding
  - Personalized gameplay advice

- 🌐 **Web Interface**:
  - Clean, responsive design
  - Markdown-supported chat
  - Easy mode switching

## Project Structure

```
StardrewAI/
├── src/
│   ├── scraper/          # Wiki scraping components
│   ├── rag/              # RAG system and vector database
│   ├── agent/            # LangChain agent implementation
│   ├── api/              # FastAPI backend
│   └── frontend/         # Web interface
├── data/                 # Scraped and processed data
├── tests/                # Unit tests
├── config/               # Configuration files
└── docs/                 # Documentation
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment**:
   ```bash
   cp .env.example .env
   # Add your OpenAI API key and other configurations
   ```

3. **Scrape Wiki Data**:
   ```bash
   python -m src.scraper.wiki_scraper
   ```

4. **Build Knowledge Base**:
   ```bash
   python -m src.rag.build_database
   ```

5. **Start the Server**:
   ```bash
   uvicorn src.api.main:app --port 8001
   ```

6. **Open your browser** to `http://localhost:8001`

## Configuration

The agent supports various configurations:
- **Response Style**: Adjust hint level vs detailed explanations
- **Game Knowledge**: Focus on specific aspects (farming, mining, relationships, etc.)
- **Spoiler Control**: Prevent revealing late-game content

## Development

- **Code Formatting**: `black src/`
- **Linting**: `ruff check src/`
- **Testing**: `pytest tests/`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.