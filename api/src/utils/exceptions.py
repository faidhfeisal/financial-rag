# In exceptions.py

class RAGSystemError(Exception):
    """Base exception for RAG system"""
    pass

class DocumentProcessingError(RAGSystemError):
    """Raised when document processing fails"""
    pass

class EmbeddingGenerationError(RAGSystemError):
    """Raised when embedding generation fails"""
    pass

class VectorStoreError(RAGSystemError):
    """Raised when vector store operations fail"""
    pass

class StorageError(RAGSystemError):
    """Raised when storage operations fail"""
    pass