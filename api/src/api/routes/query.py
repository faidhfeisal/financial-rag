from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from ...core.rag import RAGSystem
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    stream: Optional[bool] = False
    filters: Optional[Dict[str, Any]] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class Source(BaseModel):
    content: str
    metadata: Dict[str, Any]
    similarity: float

class Evaluation(BaseModel):
    confidence_score: float
    latency_ms: float
    token_usage: Dict[str, int]
    citations: Dict[str, Any]
    source_relevance: Dict[str, float]


class QueryResponse(BaseModel):
    response: str
    sources: List[Source]
    evaluation: Evaluation
    query_id: str
    usage: Usage
    confidence: float

    class Config:
        arbitrary_types_allowed = True

async def get_rag_system():
    """Dependency to get RAG system instance"""
    try:
        return RAGSystem()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def generate_stream_response(rag_system: RAGSystem, query: str, filters: Optional[Dict[str, Any]] = None):
    """Generator for SSE streaming"""
    try:
        async for chunk in rag_system.process_query_stream(query, filters):
            # Format as SSE
            yield f"data: {json.dumps(chunk)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"

@router.post("/query")
async def process_query(
    request: QueryRequest,
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """Process a query using the RAG system"""
    try:
        # If streaming is requested, redirect to streaming endpoint
        if request.stream:
            return await stream_query(request, rag_system)
        
        result = await rag_system.process_query(
            query=request.query,
            filters=request.filters
        )
        
        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.post("/query/stream")
async def stream_query(
    request: QueryRequest,
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """Stream a query response using Server-Sent Events (SSE)"""
    
    async def event_generator():
        try:
            async for event in rag_system.process_query_stream(
                query=request.query,
                filters=request.filters
            ):
                if event["type"] == "error":
                    yield f"data: {json.dumps(event)}\n\n"
                    break
                
                # Send the event
                yield f"data: {json.dumps(event)}\n\n"
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send end marker
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            error_event = {
                "type": "error",
                "data": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Transfer-Encoding': 'chunked'
        }
    )