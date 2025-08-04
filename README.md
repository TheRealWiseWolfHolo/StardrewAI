# Stardew Valley AI Chat Agent

An intelligent assistant that helps players navigate and master Stardew Valley using state-of-the-art RAG (Retrieval-Augmented Generation) technology.

## Features

- 🎮 **Two Game Modes**: Switch between subtle hints and full walkthroughs.
  - **Hints Mode**: Provides gentle guidance without spoilers for players who want to discover things on their own.
  - **Full Walkthrough Mode**: Offers detailed, step-by-step instructions for complex tasks.

- 🔍 **Smart Knowledge Base**: A rich, multi-modal knowledge base built from the official Stardew Valley Wiki.
  - **Comprehensive Wiki Scraping**: The scraper navigates the wiki using a Breadth-First Search (BFS) algorithm to discover and ingest content.
  - **Rich Data Extraction**: Goes beyond plain text to extract structured data like **infobox images** and **wiki tables**, providing a richer context for answers.
  - **Vector-based Semantic Search**: Uses **ChromaDB** and `sentence-transformers` to create a searchable vector index, allowing the agent to find the most relevant information based on meaning, not just keywords. Text is intelligently split into chunks, and tables are converted to text descriptions to make all data searchable.

- 🤖 **AI-Powered Chat**: A highly capable and context-aware agent built with **LangChain**.
  - **Intelligent Tool Use**: Leverages an **OpenAI Functions Agent** to intelligently decide which tool to use, whether it's a general knowledge search, a specific query for tables, or creating a dynamic checklist.
  - **Structured JSON Output**: The agent returns rich, structured JSON responses—not just plain text. This allows the frontend to dynamically render tables, checklists, images, and source links.
  - **Context-Aware Memory**: Remembers the last few turns of the conversation to understand follow-up questions and pronouns. It also uses the player's in-game date (year, season, day) to provide timely, relevant advice.

- 🌐 **Web Interface**: A clean and responsive web UI built with **FastAPI** and **Jinja2**.
  - **Clean, responsive design** for a smooth user experience.
  - **Markdown-supported chat** for clear formatting.
  - **Easy mode switching** and context submission.

## Project Structure

```
StardrewAI/
├── src/
│   ├── scraper/          # (scraper/wiki_scraper.py) Wiki scraping components
│   ├── rag/              # (rag/knowledge_base.py) RAG system and ChromaDB vector database
│   ├── agent/            # (agent/stardew_agent.py) LangChain agent implementation
│   ├── api/              # (api/main.py) FastAPI backend
│   └── frontend/         # (frontend/templates/index.html) Web interface
├── data/                 # Scraped and processed data
├── tests/                # Unit tests
├── config/               # Configuration files
└── docs/                 # Documentation
```

## Quick Start

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up Environment**:
    ```bash
    cp .env.example .env
    # Add your OpenAI API key and other configurations to the .env file
    ```

3.  **Scrape Wiki Data**:
    ```bash
    python -m src.scraper.wiki_scraper --force
    ```

4.  **Build Knowledge Base**:
    ```bash
    python -m src.rag.knowledge_base --force
    ```

5. **Start the Server**:
   ```bash
   uvicorn src.api.main:app --port 8001
   ```
5.  **Start the Server**:
    ```bash
    uvicorn src.api.main:app --port 8001 --reload
    ```

6. **Open your browser** to `http://localhost:8001`

## Configuration

The agent supports various configurations:
- **Response Style**: Adjust hint level vs detailed explanations
- **Game Knowledge**: Focus on specific aspects (farming, mining, relationships, etc.)
- **Spoiler Control**: Prevent revealing late-game content
6.  **Open your browser** to `http://localhost:8001`

## Development

- **Code Formatting**: `black src/`
- **Linting**: `ruff check src/`
- **Testing**: `pytest tests/`

## Contributing

1.  Fork the repository
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`)
3.  Make your changes and commit them (`git commit -m 'Add some AmazingFeature'`)
4.  Add tests for your changes
5.  Push to the branch (`git push origin feature/AmazingFeature`)
6.  Open a Pull Request

## License

MIT License - see LICENSE file for details.
