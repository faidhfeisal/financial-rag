from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routes import query, documents
from ..core.config import get_settings
from ..services.azure_client import AzureClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Check system health including Azure OpenAI connection"""
    try:
        azure_client = AzureClient()
        azure_connection = await azure_client.test_connection()
        
        return {
            "status": "healthy" if azure_connection else "degraded",
            "azure_openai": "connected" if azure_connection else "disconnected",
            "api": "running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
    
@app.get("/debug/azure")
async def debug_azure():
    """Debug Azure OpenAI connection"""
    try:
        azure_client = AzureClient()
        settings = get_settings()
        
        # Check environment variables
        env_check = {
            "has_endpoint": bool(settings.AZURE_OPENAI_ENDPOINT),
            "has_api_key": bool(settings.AZURE_OPENAI_API_KEY),
            "has_deployment_name": bool(settings.AZURE_EMBEDDING_DEPLOYMENT_NAME),
            "endpoint": settings.AZURE_OPENAI_ENDPOINT.replace(
                settings.AZURE_OPENAI_API_KEY, "***"
            ) if settings.AZURE_OPENAI_ENDPOINT else None,
            "deployment_name": settings.AZURE_EMBEDDING_DEPLOYMENT_NAME
        }
        
        # Test connection
        connection_success = await azure_client.test_connection()
        
        return {
            "environment_check": env_check,
            "connection_test": connection_success
        }
    except Exception as e:
        logger.error(f"Debug check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Include routers
app.include_router(query.router, prefix="/api/v1", tags=["queries"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])