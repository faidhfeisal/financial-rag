from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache

class Settings(BaseSettings):
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str

     # JWT Settings
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:80"]

    
    # Azure Storage Settings
    AZURE_STORAGE_CONNECTION_STRING: str
    DOCUMENTS_CONTAINER_NAME: str = "financial-documents"
    
    # Vector DB Settings
    QDRANT_HOST: str = "vectordb"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "financial_docs"

      # Vector Search Settings
    MAX_DOCUMENTS: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    VECTOR_SIZE: int = 1536  # Size for text-embedding-ada-002
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()