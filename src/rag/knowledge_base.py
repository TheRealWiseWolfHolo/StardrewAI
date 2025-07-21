"""RAG system for Stardew Valley knowledge base using ChromaDB."""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.settings import settings
except ImportError:
    # Fallback settings class
    class Settings:
        embedding_model = "all-MiniLM-L6-v2"
        chroma_db_path = "./data/chroma_db"
        scraped_data_file = "./Data/wiki_content.json"
    
    settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StardewRAGSystem:
    """Retrieval-Augmented Generation system for Stardew Valley knowledge."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.db_path = settings.chroma_db_path
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection("stardew_knowledge")
            logger.info("Loaded existing ChromaDB collection")
        except Exception:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name="stardew_knowledge",
                metadata={"description": "Stardew Valley Wiki knowledge base"}
            )
            logger.info("Created new ChromaDB collection")
    
    def process_scraped_data(self, scraped_data: List[Dict]) -> List[Dict]:
        """Process scraped wiki data into structured chunks."""
        processed_chunks = []
        
        for page in scraped_data:
            try:
                # Split content into manageable chunks
                content_chunks = self._split_content(page['content'])
                
                for i, chunk in enumerate(content_chunks):
                    if len(chunk.strip()) < 50:  # Skip very short chunks
                        continue
                    
                    chunk_data = {
                        'id': f"{page['title']}_{i}",
                        'title': page['title'],
                        'url': page['url'],
                        'content': chunk,
                        'chunk_index': i,
                        'source_type': 'wiki_content'
                    }
                    
                    # Add infobox data if available
                    if page.get('infobox'):
                        chunk_data['infobox'] = page['infobox']
                    
                    processed_chunks.append(chunk_data)
                
                # Process tables separately
                for j, table in enumerate(page.get('tables', [])):
                    table_content = self._table_to_text(table)
                    if table_content:
                        table_chunk = {
                            'id': f"{page['title']}_table_{j}",
                            'title': f"{page['title']} - Table {j+1}",
                            'url': page['url'],
                            'content': table_content,
                            'chunk_index': -1,  # Special index for tables
                            'source_type': 'table_data',
                            'table_data': table
                        }
                        processed_chunks.append(table_chunk)
                
            except Exception as e:
                logger.warning(f"Error processing page {page.get('title', 'Unknown')}: {str(e)}")
                continue
        
        logger.info(f"Processed {len(processed_chunks)} chunks from {len(scraped_data)} pages")
        return processed_chunks
    
    def _split_content(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """Split content into chunks while preserving context."""
        if not content:
            return []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += f"\n\n{paragraph}" if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _table_to_text(self, table: Dict) -> str:
        """Convert table data to readable text."""
        if not table.get('headers') or not table.get('rows'):
            return ""
        
        headers = table['headers']
        rows = table['rows']
        
        # Create a text representation of the table
        text_parts = [f"Table with columns: {', '.join(headers)}"]
        
        for row in rows[:10]:  # Limit to first 10 rows
            if len(row) == len(headers):
                row_text = []
                for header, value in zip(headers, row):
                    if value.strip():
                        row_text.append(f"{header}: {value}")
                if row_text:
                    text_parts.append(" | ".join(row_text))
        
        return "\n".join(text_parts)
    
    def build_vector_database(self, processed_chunks: Optional[List[Dict]] = None) -> int:
        """Build vector database from processed chunks."""
        if processed_chunks is None:
            # Load from scraped data
            try:
                with open(settings.scraped_data_file, 'r', encoding='utf-8') as f:
                    scraped_data = json.load(f)
                processed_chunks = self.process_scraped_data(scraped_data)
            except FileNotFoundError:
                logger.error(f"No scraped data found at {settings.scraped_data_file}")
                return 0
        
        if not processed_chunks:
            logger.error("No processed chunks to add to database")
            return 0
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for chunk in processed_chunks:
            documents.append(chunk['content'])
            metadatas.append({
                'title': chunk['title'],
                'url': chunk['url'],
                'chunk_index': chunk['chunk_index'],
                'source_type': chunk['source_type']
            })
            ids.append(chunk['id'])
        
        # Add to collection in batches
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            try:
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                total_added += len(batch_docs)
                logger.info(f"Added batch {i//batch_size + 1}, total: {total_added}")
                
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {str(e)}")
                continue
        
        logger.info(f"Successfully added {total_added} chunks to vector database")
        return total_added
    
    def search(self, query: str, n_results: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Search the knowledge base for relevant content."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results.get('distances') else None
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return []
    
    def get_context_for_query(self, query: str, max_chunks: int = 3) -> str:
        """Get relevant context for a query."""
        search_results = self.search(query, n_results=max_chunks)
        
        if not search_results:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for result in search_results:
            title = result['metadata'].get('title', 'Unknown')
            content = result['content']
            context_parts.append(f"From '{title}':\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def reset_database(self):
        """Reset the vector database (use with caution)."""
        try:
            self.client.delete_collection("stardew_knowledge")
            self.collection = self.client.create_collection(
                name="stardew_knowledge",
                metadata={"description": "Stardew Valley Wiki knowledge base"}
            )
            logger.info("Database reset successfully")
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")


def main():
    """Build the vector database from scraped data."""
    rag_system = StardewRAGSystem()
    
    # Check if database already has content
    try:
        count = rag_system.collection.count()
        if count > 0:
            logger.info(f"Database already contains {count} documents")
            response = input("Do you want to rebuild? (y/N): ")
            if response.lower() != 'y':
                return
            rag_system.reset_database()
    except Exception:
        pass
    
    # Build the database
    chunks_added = rag_system.build_vector_database()
    
    if chunks_added > 0:
        logger.info("Vector database built successfully!")
        
        # Test search functionality
        test_query = "How do I grow crops in Stardew Valley?"
        results = rag_system.search(test_query, n_results=3)
        logger.info(f"Test search for '{test_query}' returned {len(results)} results")
    else:
        logger.error("Failed to build vector database")


if __name__ == "__main__":
    main()
