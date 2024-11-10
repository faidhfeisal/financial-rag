from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel
from ...core.rag import RAGSystem
from ...core.security import requires_auth, Permission
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False

class QueryResponse(BaseModel):
    response: str
    sources: list
    evaluation: Dict[str, Any]
    query_id: str
    usage: Dict[str, int]
    confidence: float

async def get_rag_system():
    """Dependency to get RAG system instance"""
    return RAGSystem()

@router.post("/stream")
async def stream_query(
    request: QueryRequest,
    rag_system: RAGSystem = Depends(get_rag_system),
    user=Depends(requires_auth([Permission.QUERY_SYSTEM]))
):
    """Stream a query response using Server-Sent Events (SSE)"""
    try:
        # Add user context to request
        request.filters = request.filters or {}
        request.filters["user_id"] = user["id"]
        
        async def event_generator():
            try:
                async for event in rag_system.process_query_stream(
                    query=request.query,
                    filters=request.filters,
                    user_context=user
                ):
                    # Convert event dictionary to JSON string
                    event_json = json.dumps(event)
                    yield f"data: {event_json}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Stream error: {str(e)}")
                error_event = json.dumps({
                    "type": "error",
                    "data": str(e)
                })
                yield f"data: {error_event}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Transfer-Encoding": "chunked"
            }
        )
    except Exception as e:
        logger.error(f"Query stream error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    rag_system: RAGSystem = Depends(get_rag_system),
    user=Depends(requires_auth([Permission.QUERY_SYSTEM]))
):
    """Process a query using the RAG system"""
    try:
        # Add user context to request
        request.filters = request.filters or {}
        request.filters["user_id"] = user["id"]

        result = await rag_system.process_query(
            query=request.query,
            filters=request.filters,
            user_context=user
        )
        return result
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )