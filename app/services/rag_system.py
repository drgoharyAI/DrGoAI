"""RAG System for Medical Knowledge Base"""
import os
from loguru import logger

class RAGSystem:
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.initialized = False
        self.initialization_error = None
        self.documents = []
        self.total_chunks = 0
        self.total_size = 0
        
    def initialize(self):
        """Initialize ChromaDB connection"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create persistent directory
            persist_dir = "data/chroma_db"
            os.makedirs(persist_dir, exist_ok=True)
            
            # Initialize ChromaDB with persistent storage
            self.chroma_client = chromadb.PersistentClient(path=persist_dir)
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="medical_policies",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.initialized = True
            self.initialization_error = None
            logger.info("✓ RAG System initialized successfully")
            
        except ImportError:
            self.initialization_error = "ChromaDB not installed"
            logger.warning(f"RAG: ChromaDB not installed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"RAG Initialization Error: {e}")
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            if not self.initialized:
                return {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "total_size_mb": 0.0,
                    "status": "not_initialized",
                    "error": self.initialization_error
                }
            
            # Get collection count
            collection_count = self.collection.count() if self.collection else 0
            
            return {
                "total_documents": len(self.documents),
                "total_chunks": collection_count,
                "total_size_mb": round(self.total_size / 1024 / 1024, 2),
                "status": "operational",
                "embedding_model": "default",
                "error": None
            }
        except Exception as e:
            logger.error(f"Error getting RAG stats: {e}")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "total_size_mb": 0.0,
                "status": "error",
                "error": str(e)
            }
    
    def search_policies(self, query: str, top_k: int = 5):
        """Search policy database"""
        if not self.initialized:
            return []
        
        try:
            if self.collection and self.collection.count() > 0:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k
                )
                return results.get("documents", [[]])[0]
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def add_policy_document(self, content: str, metadata: dict):
        """Add policy document to ChromaDB"""
        if not self.initialized:
            raise RuntimeError("RAG system not initialized")
        
        try:
            doc_id = f"doc_{len(self.documents)}"
            self.documents.append({
                "id": doc_id,
                "content": content,
                "metadata": metadata
            })
            self.total_size += len(content.encode('utf-8'))
            
            # Add to collection
            if self.collection:
                self.collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[metadata]
                )
            
            return 1
        except Exception as e:
            logger.error(f"Error adding policy: {e}")
            raise

# Initialize RAG system on import
rag_system = RAGSystem()
try:
    rag_system.initialize()
except Exception as e:
    logger.warning(f"RAG system init error: {e}")
