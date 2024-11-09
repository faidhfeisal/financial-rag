from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
import numpy as np
from ..core.config import get_settings
from ..services.azure_client import AzureClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EvaluationMetrics(BaseModel):
    query_id: str
    timestamp: datetime
    latency_ms: float
    token_usage: Dict[str, int]
    source_count: int
    source_relevance_scores: List[float]
    response_length: int
    confidence_score: float
    has_citations: bool
    user_feedback: Optional[Dict[str, Any]] = None

class ResponseEvaluation:
    def __init__(self):
        self.settings = get_settings()
        self.azure_client = AzureClient()

    async def evaluate_response(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        execution_time: float,
        token_usage: Dict[str, int]
    ) -> Dict[str, Any]:
        """Evaluate the response quality and relevance"""
        try:
            metrics = {
                "query_id": f"query_{datetime.utcnow().timestamp()}",
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": execution_time * 1000,
                "token_usage": token_usage,
                "response_length": len(response),
                "source_count": len(sources),
                "citations": {
                    "count": sum(1 for i in range(len(sources)) if f"[{i+1}]" in response),
                    "present": any(f"[{i+1}]" in response for i in range(len(sources)))
                },
                "source_relevance": {
                    "mean": sum(s.get("similarity", 0) for s in sources) / len(sources) if sources else 0,
                },
                "confidence_score": sum(s.get("similarity", 0) for s in sources) / len(sources) if sources else 0
            }

            # Store metrics but don't wait for it
            try:
                await self._store_metrics(metrics)
            except Exception as e:
                logger.warning(f"Failed to store metrics: {str(e)}")

            return metrics

        except Exception as e:
            logger.error(f"Error evaluating response: {str(e)}")
            return {
                "error": str(e),
                "latency_ms": execution_time * 1000,
                "token_usage": token_usage
            }

    async def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store evaluation metrics"""
        try:
            container_name = "evaluation-logs"
            timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
            blob_name = f"evaluations/{metrics['query_id']}/{timestamp}.json"
            
            # Store metrics but don't raise exceptions
            await self.azure_client.store_json(
                container_name=container_name,
                blob_name=blob_name,
                data=metrics
            )
        except Exception as e:
            logger.warning(f"Failed to store metrics: {str(e)}")

    def _calculate_cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _calculate_confidence_score(
        self,
        query_relevance: float,
        source_relevance: float,
        has_citations: bool
    ) -> float:
        """Calculate overall confidence score"""
        weights = {
            "query_relevance": 0.4,
            "source_relevance": 0.4,
            "citations": 0.2
        }
        
        citation_score = 1.0 if has_citations else 0.5
        
        return (
            weights["query_relevance"] * query_relevance +
            weights["source_relevance"] * source_relevance +
            weights["citations"] * citation_score
        )

    async def _store_evaluation(self, metrics: Dict[str, Any]):
        """Store evaluation metrics in Azure Blob Storage"""
        try:
            container_name = "evaluation-logs"
            timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
            blob_name = f"evaluations/{metrics['query_id']}/{timestamp}.json"
            
            result = await self.azure_client.store_json(
                container_name=container_name,
                blob_name=blob_name,
                data=metrics
            )
            
            if result:
                logger.info(f"Stored evaluation metrics: {blob_name}")
            else:
                logger.warning("Failed to store evaluation metrics but continuing")
                
        except Exception as e:
            logger.error(f"Error storing evaluation: {str(e)}")
            # Don't raise the exception - just log it and continue

class UserFeedback(BaseModel):
    query_id: str
    rating: int  # 1-5
    helpful: bool
    feedback_text: Optional[str] = None
    categories: Optional[List[str]] = None

class FeedbackCollector:
    def __init__(self):
        self.settings = get_settings()
        self.azure_client = AzureClient()

    async def record_feedback(
        self,
        feedback: UserFeedback
    ) -> Dict[str, Any]:
        """Record and analyze user feedback"""
        try:
            feedback_data = feedback.dict()
            feedback_data["timestamp"] = datetime.utcnow()
            
            # Analyze feedback text if provided
            if feedback.feedback_text:
                sentiment = await self.azure_client.analyze_sentiment(
                    feedback.feedback_text
                )
                feedback_data["sentiment"] = sentiment

            # Store feedback
            container_name = "evaluation-logs"
            blob_name = f"feedback/{feedback.query_id}.json"
            
            await self.azure_client.store_json(
                container_name,
                blob_name,
                feedback_data
            )

            return feedback_data

        except Exception as e:
            raise Exception(f"Error recording feedback: {str(e)}")