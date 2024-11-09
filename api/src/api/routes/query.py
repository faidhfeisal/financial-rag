from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
from ...core.rag import RAGSystem
from ...core.config import get_settings
import logging
logger = logging.getLogger(__name__)


router = APIRouter()

class QueryRequest(BaseModel):
    query: str
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

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    rag_system: RAGSystem = Depends(get_rag_system)
):
    """Process a query using the RAG system"""
    try:
        result = await rag_system.process_query(
            query=request.query,
            filters=request.filters
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to process query"
            )

        # Format the response according to the model
        response = QueryResponse(
            response=result["response"],
            sources=[Source(**source) for source in result["sources"]],
            evaluation=Evaluation(**result["evaluation"]),
            query_id=result.get("query_id", ""),
            usage=Usage(**result["usage"]),
            confidence=result["evaluation"]["confidence_score"]
        )
        
        return response
        
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
    return StreamingResponse(
        generate_stream_response(
            rag_system,
            request.query,
            request.filters
        ),
        media_type="text/event-stream"
    )