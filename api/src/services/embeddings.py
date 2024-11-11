from typing import List, Dict, Any, Optional, Union
import numpy as np
import asyncio
from datetime import datetime, timedelta
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import redis
from ..core.config import get_settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingsService:
    def __init__(self):
        self.settings = get_settings()
        self.azure_client = None  # Lazy initialization
        self.cache = redis.Redis(
            host=self.settings.REDIS_HOST,
            port=self.settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        self.cache_ttl = timedelta(days=7)  # Cache embeddings for 7 days
        self.batch_size = 5  # Number of texts to process in parallel

    async def _init_azure_client(self):
        """Lazy initialization of Azure client"""
        if self.azure_client is None:
            from ..services.azure_client import AzureClient
            self.azure_client = AzureClient()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        use_cache: bool = True
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for one or more texts"""
        await self._init_azure_client()
        
        # Handle single text input
        if isinstance(texts, str):
            return await self._generate_single_embedding(texts, use_cache)
            
        # Handle batch processing
        return await self._generate_batch_embeddings(texts, use_cache)

    async def _generate_single_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> List[float]:
        """Generate embedding for a single text"""
        if use_cache:
            cached_embedding = await self._get_cached_embedding(text)
            if cached_embedding:
                return cached_embedding

        embedding = await self.azure_client.generate_embedding(text)
        
        if use_cache:
            await self._cache_embedding(text, embedding)
            
        return embedding

    async def _generate_batch_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        results = []
        batch = []
        cached_indices = set()

        # Check cache first
        if use_cache:
            for i, text in enumerate(texts):
                cached_embedding = await self._get_cached_embedding(text)
                if cached_embedding:
                    results.append(cached_embedding)
                    cached_indices.add(i)
                else:
                    batch.append((i, text))
        else:
            batch = list(enumerate(texts))

        # Process remaining texts in batches
        all_embeddings = []
        for i in range(0, len(batch), self.batch_size):
            batch_slice = batch[i:i + self.batch_size]
            batch_texts = [text for _, text in batch_slice]
            
            # Generate embeddings in parallel
            tasks = [
                self.azure_client.generate_embedding(text)
                for text in batch_texts
            ]
            batch_embeddings = await asyncio.gather(*tasks)
            
            # Cache the new embeddings
            if use_cache:
                cache_tasks = [
                    self._cache_embedding(text, emb)
                    for text, emb in zip(batch_texts, batch_embeddings)
                ]
                await asyncio.gather(*cache_tasks)
            
            all_embeddings.extend(batch_embeddings)

        # Combine cached and new embeddings in correct order
        final_embeddings = [None] * len(texts)
        embedding_idx = 0
        
        for i in range(len(texts)):
            if i in cached_indices:
                final_embeddings[i] = results[embedding_idx]
                embedding_idx += 1
            else:
                final_embeddings[i] = all_embeddings.pop(0)

        return final_embeddings

    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        try:
            cache_key = self._get_cache_key(text)
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Cache retrieval error: {str(e)}")
            return None

    async def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache an embedding"""
        try:
            cache_key = self._get_cache_key(text)
            self.cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(embedding)
            )
        except Exception as e:
            print(f"Cache storage error: {str(e)}")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        import hashlib
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()}"

    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings"""
        return np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

    async def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find most similar embeddings from a list of candidates"""
        similarities = [
            await self.compute_similarity(query_embedding, emb)
            for emb in candidate_embeddings
        ]
        
        # Get indices of top k similar embeddings
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [
            {
                "index": int(idx),
                "similarity": float(similarities[idx])
            }
            for idx in top_indices
        ]
    
    async def clear_document_cache(self, document_id: str) -> None:
        """Clear cached embeddings for a specific document"""
        try:
            pattern = f"emb:doc:{document_id}:*"
            keys = self.cache.keys(pattern)
            if keys:
                self.cache.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached embeddings for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to clear embeddings cache: {str(e)}")
            raise