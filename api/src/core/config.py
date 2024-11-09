from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

class Settings(BaseSettings):
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str
    
    
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_BATCH_SIZE: int = 5
    EMBEDDING_CACHE_TTL_DAYS: int = 7
    EMBEDDING_MAX_TOKENS: int = 8191  # Maximum tokens for ada-002

     # Redis Settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # Chunking Settings
    CHUNK_MAX_TOKENS: int = 500  # Target tokens per chunk
    CHUNK_OVERLAP_TOKENS: int = 50
    
    # Azure Storage Settings
    AZURE_STORAGE_CONNECTION_STRING: str
    DOCUMENTS_CONTAINER_NAME: str = "financial-documents"
    
    # Vector DB Settings
    QDRANT_HOST: str = "vectordb"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "financial_docs"
    VECTOR_SIZE: int = 1536  # Size of ada-002 embeddings
    
    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_DOCUMENTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    @property
    def formatted_endpoint(self) -> str:
        """Ensure endpoint is properly formatted"""
        endpoint = self.AZURE_OPENAI_ENDPOINT.strip()
        parsed = urlparse(endpoint)
        if not parsed.scheme:
            endpoint = f'https://{endpoint}'
        if not endpoint.endswith('/'):
            endpoint += '/'
        return endpoint

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.AZURE_OPENAI_ENDPOINT = self.formatted_endpoint

@lru_cache()
def get_settings() -> Settings:
    return Settings()


# curl -v https://financial-rag.openai.azure.com/openai/deployments/YOUR_GPT_DEPLOYMENT/chat/completions?api-version=2024-02-15-preview \
#   -H "Content-Type: application/json" \
#   -H "api-key: D3opBQS7oT12SGSg5aXnJVfnqNDIKAKGFyphh7kZbbC04e2NWNebJQQJ99AKACmepeSXJ3w3AAABACOG7Oex" \
#   -d '{
#     "messages": [
#       {
#         "role": "user",
#         "content": "Say hello!"
#       }
#     ],
#     "model": "gpt-4"
#   }'