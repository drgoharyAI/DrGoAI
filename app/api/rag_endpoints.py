"""
RAG System Endpoints - Document management and RAG operations
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from app.services.rag_system import rag_system

router = APIRouter(prefix="/rag", tags=["RAG"])

@router.get("/health", summary="RAG System Health Check")
async def health_check():
    """Check if RAG system is properly initialized"""
    return {
        "initialized": rag_system.initialized,
        "status": "operational" if rag_system.initialized else "initializing",
        "error": rag_system.initialization_error,
        "timestamp": datetime.utcnow()
    }

@router.get("/stats", summary="RAG System Statistics")
async def get_stats():
    """Get RAG system statistics"""
    try:
        stats = rag_system.get_database_stats()
        return {
            "initialized": rag_system.initialized,
            "stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return {
            "initialized": False,
            "stats": {
                "total_documents": 0,
                "total_chunks": 0,
                "total_size_mb": 0.0,
                "status": "error",
                "error": str(e)
            },
            "timestamp": datetime.utcnow()
        }

@router.get("/database/stats", summary="RAG Database Statistics")
async def get_database_stats():
    """Get RAG database statistics"""
    try:
        stats = rag_system.get_database_stats()
        return {
            "initialized": rag_system.initialized,
            "stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "initialized": False,
            "stats": {
                "total_documents": 0,
                "total_chunks": 0,
                "total_size_mb": 0.0,
                "status": "error",
                "error": str(e)
            },
            "timestamp": datetime.utcnow()
        }

@router.get("/documents", summary="List Documents")
async def list_documents():
    """List all documents in RAG system"""
    try:
        if not rag_system.initialized:
            return {
                "initialized": False,
                "error": rag_system.initialization_error,
                "documents": [],
                "total": 0,
                "timestamp": datetime.utcnow()
            }
        
        return {
            "initialized": True,
            "documents": rag_system.documents,
            "total": len(rag_system.documents),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {
            "error": str(e),
            "documents": [],
            "total": 0,
            "timestamp": datetime.utcnow()
        }

@router.post("/upload", summary="Upload Document")
async def upload_document(file: UploadFile = File(...)):
    """Upload document to RAG system"""
    if not rag_system.initialized:
        return {
            "success": False,
            "error": f"RAG not initialized: {rag_system.initialization_error}",
            "filename": file.filename,
            "timestamp": datetime.utcnow()
        }
    
    try:
        content = await file.read()
        metadata = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content)
        }
        
        chunks_added = rag_system.add_policy_document(
            content.decode('utf-8', errors='ignore'),
            metadata
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "chunks_added": chunks_added,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error uploading: {e}")
        return {
            "success": False,
            "error": str(e),
            "filename": file.filename,
            "timestamp": datetime.utcnow()
        }

@router.post("/search", summary="Search RAG Database")
async def search_rag(query: str):
    """Search RAG database"""
    if not rag_system.initialized:
        return {
            "query": query,
            "error": rag_system.initialization_error,
            "results": [],
            "total": 0,
            "timestamp": datetime.utcnow()
        }
    
    try:
        results = rag_system.search_policies(query)
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            "query": query,
            "error": str(e),
            "results": [],
            "total": 0,
            "timestamp": datetime.utcnow()
        }
