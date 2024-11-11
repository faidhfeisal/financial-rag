from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .routes import documents, query, auth
from ..core.config import get_settings
import logging
import psutil
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    yield
    # Shutdown
    logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

@app.middleware("http")
async def monitor_memory(request: Request, call_next):
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024
    
    response = await call_next(request)
    
    current_memory = process.memory_info().rss / 1024 / 1024
    logger.info(
        f"Request to {request.url.path} completed. "
        f"Memory usage: {current_memory:.2f}MB "
        f"(Delta: {(current_memory - start_memory):.2f}MB)"
    )
    
    return response

# Include routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["auth"]
)
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["documents"]
)
app.include_router(
    query.router,
    prefix="/api/v1/query",
    tags=["query"]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}