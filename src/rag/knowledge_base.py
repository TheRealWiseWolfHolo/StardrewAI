"""RAG system for Stardew Valley knowledge base using ChromaDB."""

import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.settings import settings
except ImportError:
    class Settings:
        embedding_model = "all-MiniLM-L6-v2"
        chroma_db_path = "./data/chroma_db"
        scraped_data_file = "./data/wiki_content.json"
    settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StardewRAGSystem:
    """RAG system for Stardew Valley, now supporting rich data like images and tables."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.db_path = settings.chroma_db_path
        
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
        
        # We get the collection dynamically in the search function to avoid stale references
        self.collection_name = "stardew_knowledge"
        logger.info(f"RAG system initialized for collection '{self.collection_name}'")

    def process_scraped_data(self, scraped_data: List[Dict]) -> List[Dict]:
        """Processes scraped data into chunks, preserving rich metadata."""
        processed_chunks = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        
        for page in scraped_data:
            try:
                base_meta = {
                    'url': page['url'],
                    'title': page['title'],
                    'image_url': page.get('image_url')
                }
                content_chunks = text_splitter.split_text(page['content'])
                for i, chunk_text in enumerate(content_chunks):
                    if len(chunk_text.strip()) < 50: continue
                    processed_chunks.append({
                        'id': f"{page['url']}_content_{i}",
                        'content': chunk_text,
                        'metadata': {**base_meta, 'source_type': 'text'}
                    })
                for j, table_data in enumerate(page.get('tables', [])):
                    table_text_representation = self._table_to_text(table_data)
                    if not table_text_representation: continue
                    processed_chunks.append({
                        'id': f"{page['url']}_table_{j}",
                        'content': table_text_representation,
                        'metadata': {
                            **base_meta,
                            'source_type': 'table',
                            'table_json': json.dumps(table_data)
                        }
                    })
            except Exception as e:
                logger.warning(f"Error processing page {page.get('title', 'Unknown')}: {e}")
        
        logger.info(f"Processed {len(processed_chunks)} total chunks from {len(scraped_data)} pages.")
        return processed_chunks
    
    def _table_to_text(self, table: Dict) -> str:
        if not table.get('headers') or not table.get('rows'): return ""
        title = table.get('title', 'This table')
        headers = table['headers']
        text_parts = [f"{title} with columns: {', '.join(headers)}."]
        for row in table['rows'][:5]:
            if len(row) == len(headers):
                row_text = [f"{headers[i]}: {cell}" for i, cell in enumerate(row) if str(cell).strip()]
                if row_text: text_parts.append(" | ".join(row_text))
        return "\n".join(text_parts)
    
    def build_vector_database(self, force_rebuild: bool = False) -> int:
        """Builds the vector database with rich metadata."""
        collection = self.client.get_or_create_collection(self.collection_name)
        if collection.count() > 0 and not force_rebuild:
            logger.info(f"Database has {collection.count()} docs. Use --force to rebuild.")
            return 0
            
        if force_rebuild: self.reset_database()
        collection = self.client.get_or_create_collection(self.collection_name)

        try:
            with open(settings.scraped_data_file, 'r', encoding='utf-8') as f:
                scraped_data = json.load(f)
            processed_chunks = self.process_scraped_data(scraped_data)
        except FileNotFoundError:
            logger.error(f"Scraped data file not found at {settings.scraped_data_file}.")
            return 0
        
        if not processed_chunks: return 0
        
        documents = [chunk['content'] for chunk in processed_chunks]
        raw_metadatas = [chunk['metadata'] for chunk in processed_chunks]
        ids = [chunk['id'] for chunk in processed_chunks]
        metadatas = [{k: v for k, v in meta.items() if v is not None} for meta in raw_metadatas]
        
        batch_size = 128
        total_added = 0
        for i in range(0, len(documents), batch_size):
            try:
                collection.add(
                    ids=ids[i:i + batch_size],
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size]
                )
                total_added += len(ids[i:i + batch_size])
                logger.info(f"Added batch {i//batch_size + 1}, total docs: {total_added}/{len(documents)}")
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {e}", exc_info=True)
        
        logger.info(f"Successfully added {total_added} chunks to DB.")
        return total_added
    
    def search(self, query: str, n_results: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Searches the knowledge base, ensuring a fresh collection object is used."""
        try:
            # FIX: Re-fetch the collection object to avoid stale references after reloads.
            collection = self.client.get_collection(name=self.collection_name)
            
            results = collection.query(
                query_texts=[query], n_results=n_results, where=filter_dict
            )
            
            formatted_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    if metadata.get('source_type') == 'table' and 'table_json' in metadata:
                        metadata['table'] = json.loads(metadata['table_json'])
                        del metadata['table_json']
                    formatted_results.append({
                        'content': doc, 'metadata': metadata,
                        'distance': results['distances'][0][i]
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching KB: {e}", exc_info=True)
            return []

    def reset_database(self):
        """Resets the vector database."""
        logger.info("Resetting ChromaDB collection...")
        self.client.delete_collection(name=self.collection_name)
        logger.info("Database reset successfully.")

def main():
    parser = argparse.ArgumentParser(description='Build Stardew Valley RAG KB with rich data.')
    parser.add_argument('--force', action='store_true', help='Force rebuild of the database.')
    args = parser.parse_args()

    rag_system = StardewRAGSystem()
    chunks_added = rag_system.build_vector_database(force_rebuild=args.force)
    
    if chunks_added > 0:
        logger.info(f"DB built successfully! Total docs in collection: {rag_system.client.get_collection(rag_system.collection_name).count()}")
    else:
        logger.info("No new chunks were added to the database.")

if __name__ == "__main__":
    main()