from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...services.evaluation import ResponseEvaluation, UserFeedback, FeedbackCollector

router = APIRouter()

class EvaluationResponse(BaseModel):
    metrics: Dict[str, Any]
    recommendations: List[str]

class EvaluationSummary(BaseModel):
    total_queries: int
    average_latency_ms: float
    average_confidence: float
    source_statistics: Dict[str, Any]
    citation_rate: float
    user_satisfaction: Optional[float]

@router.get("/evaluation/metrics/{query_id}")
async def get_evaluation_metrics(
    query_id: str,
    evaluator: ResponseEvaluation = Depends(lambda: ResponseEvaluation())
):
    """Get evaluation metrics for a specific query"""
    try:
        metrics = await evaluator.get_metrics(query_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Metrics not found")
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluation/summary", response_model=EvaluationSummary)
async def get_evaluation_summary(
    time_window: Optional[int] = Query(7, description="Time window in days"),
    evaluator: ResponseEvaluation = Depends(lambda: ResponseEvaluation())
):
    """Get evaluation summary for a time window"""
    try:
        start_date = datetime.utcnow() - timedelta(days=time_window)
        metrics = await evaluator.get_summary(start_date)
        return EvaluationSummary(**metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluation/feedback")
async def submit_feedback(
    feedback: UserFeedback,
    feedback_collector: FeedbackCollector = Depends(lambda: FeedbackCollector())
):
    """Submit user feedback for a query"""
    try:
        result = await feedback_collector.record_feedback(feedback)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluation/feedback/summary")
async def get_feedback_summary(
    time_window: Optional[int] = Query(7, description="Time window in days"),
    feedback_collector: FeedbackCollector = Depends(lambda: FeedbackCollector())
):
    """Get summary of user feedback"""
    try:
        start_date = datetime.utcnow() - timedelta(days=time_window)
        summary = await feedback_collector.get_summary(start_date)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))