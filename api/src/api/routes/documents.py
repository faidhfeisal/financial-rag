from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import json
from ...core.rag import RAGSystem
from ...core.security import SecurityHandler, Permission, requires_auth
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class DocumentMetadata(BaseModel):
    document_id: Optional[str] = None
    title: str
    document_type: str
    source: Optional[str] = None
    tags: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

class DocumentResponse(BaseModel):
    document_id: str
    url: str
    status: str
    metadata: Dict[str, Any]

class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int

async def get_rag_system():
    return RAGSystem()

@router.post(
    "/upload",
    response_model=DocumentResponse,
    dependencies=[Depends(requires_auth([Permission.WRITE_DOCUMENTS]))]
)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    rag_system: RAGSystem = Depends(get_rag_system),
    user=Depends(requires_auth())
):
    """Upload and process a document"""
    try:
        # Parse metadata
        try:
            metadata_dict = json.loads(metadata)
            metadata_obj = DocumentMetadata(**metadata_dict)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid metadata format: {str(e)}"
            )

        # Read file content
        content = await file.read()
        
        # Add user information to metadata
        metadata_dict = metadata_obj.dict()
        metadata_dict["created_by"] = user["id"]
        metadata_dict["created_at"] = datetime.utcnow()
        
        if not metadata_dict.get("document_id"):
            metadata_dict["document_id"] = f"doc_{datetime.utcnow().timestamp()}"

        # Process document
        result = await rag_system.ingest_document(
            content=content.decode(),
            metadata=metadata_dict,
            user_context=user
        )
        
        return DocumentResponse(
            document_id=result["document_id"],
            url=result["url"],
            status="success",
            metadata=metadata_dict
        )

    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get(
    "/",
    response_model=DocumentListResponse,
    dependencies=[Depends(requires_auth([Permission.READ_DOCUMENTS]))]
)
async def list_documents(
    document_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    rag_system: RAGSystem = Depends(get_rag_system),
    user=Depends(requires_auth())
):
    """List available documents"""
    try:
        result = await rag_system.list_documents(
            document_type=document_type,
            tag=tag,
            limit=limit,
            offset=offset,
            user_context=user
        )
        return result
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.delete(
    "/{document_id}",
    dependencies=[Depends(requires_auth([Permission.DELETE_DOCUMENTS]))]
)
async def delete_document(
    document_id: str,
    rag_system: RAGSystem = Depends(get_rag_system),
    user=Depends(requires_auth())
):
    """Delete a document"""
    try:
        result = await rag_system.delete_document(
            document_id,
            user_context=user
        )
        return result
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )