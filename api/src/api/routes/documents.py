from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
from ...core.rag import RAGSystem
from ...core.config import get_settings

router = APIRouter()

class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int

class DeleteResponse(BaseModel):
    document_id: str
    status: str
    vector_store_deleted: bool
    blob_storage_deleted: bool

class DocumentMetadata(BaseModel):
    document_id: Optional[str] = None
    title: str
    document_type: str
    source: Optional[str] = None
    tags: Optional[List[str]] = []
    created_at: Optional[datetime] = None

class IngestResponse(BaseModel):
    document_id: str
    url: str
    chunk_count: int
    status: str

async def get_rag_system():
    return RAGSystem()

@router.post("/documents/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: DocumentMetadata = None,
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """Upload and ingest a document"""
    try:
        # Read file content
        content = await file.read()
        
        # Prepare metadata
        meta_dict = metadata.dict() if metadata else {}
        if not meta_dict.get("document_id"):
            meta_dict["document_id"] = f"doc_{datetime.utcnow().timestamp()}"
        if not meta_dict.get("created_at"):
            meta_dict["created_at"] = datetime.utcnow()
            
        # Process document
        result = await rag_system.ingest_document(
            content=content.decode(),
            metadata=meta_dict
        )
        
        return IngestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    document_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """List ingested documents"""
    try:
        result = await rag_system.list_documents(
            document_type=document_type,
            tag=tag,
            limit=limit,
            offset=offset
        )
        return DocumentListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """Delete a document"""
    try:
        result = await rag_system.delete_document(document_id)
        return DeleteResponse(**result)
    except Exception as e:
        if "Document not found" in str(e):
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=str(e))