from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    Match,
    SearchRequest
)
from datetime import datetime
from ..core.config import get_settings
import uuid
import logging

logger = logging.getLogger(__name__)



class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = QdrantClient(
            host=self.settings.QDRANT_HOST,
            port=self.settings.QDRANT_PORT
        )
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure collection exists with proper configuration"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.settings.COLLECTION_NAME not in collection_names:
                logger.info(f"Creating collection: {self.settings.COLLECTION_NAME}")
                self.client.create_collection(
                    collection_name=self.settings.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.settings.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Collection created successfully")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise

    async def store_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store document chunks with their embeddings"""
        try:
            points = []
            
            # Generate base UUID for document
            base_uuid = uuid.uuid4()
            
            for i, chunk in enumerate(chunks):
                # Create a deterministic UUID for each chunk based on document ID and chunk index
                chunk_uuid = uuid.uuid5(base_uuid, f"{metadata['document_id']}_{i}")
                
                # Clean metadata by converting all values to string format
                clean_metadata = {
                    k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                    for k, v in metadata.items()
                }

                # Add chunk-specific metadata
                chunk_metadata = {
                    **clean_metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content_length": len(chunk["content"]),
                    "embedding_timestamp": datetime.utcnow().isoformat()
                }

                point = PointStruct(
                    id=str(chunk_uuid),  # Convert UUID to string
                    vector=chunk["embedding"],
                    payload={
                        "document_id": metadata["document_id"],
                        "content": chunk["content"],
                        "metadata": chunk_metadata
                    }
                )
                points.append(point)

            logger.info(f"Storing {len(points)} points in vector store")
            
            # Store points in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.settings.COLLECTION_NAME,
                    points=batch,
                    wait=True  # Ensure points are indexed before continuing
                )
                logger.info(f"Stored batch of {len(batch)} points")

            return True
            
        except Exception as e:
            error_msg = f"Error storing embeddings: {str(e)}"
            if hasattr(e, 'response'):
                error_msg += f"\nRaw response content:\n{e.response.content}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def search_similar(
        self,
        query_embedding: List[float],
        filter_criteria: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            filter_conditions = None
            if filter_criteria:
                conditions = []
                for key, value in filter_criteria.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=Match(value=value)
                        )
                    )
                filter_conditions = Filter(must=conditions)

            results = self.client.search(
                collection_name=self.settings.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=filter_conditions,
                limit=self.settings.MAX_DOCUMENTS,
                score_threshold=self.settings.SIMILARITY_THRESHOLD
            )

            return [{
                "content": result.payload["content"],
                "metadata": result.payload["metadata"],
                "similarity": result.score
            } for result in results]
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise Exception(f"Error searching vectors: {str(e)}")


    async def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List documents with optional filtering"""
        try:
            # Build filter conditions
            filter_conditions = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        conditions.append(
                            FieldCondition(
                                key=f"metadata.{key}",
                                match=Match(any=value)
                            )
                        )
                    else:
                        conditions.append(
                            FieldCondition(
                                key=f"metadata.{key}",
                                match=Match(value=value)
                            )
                        )
                filter_conditions = Filter(must=conditions)

            # Get unique document IDs and their metadata
            search_result = self.client.scroll(
                collection_name=self.settings.COLLECTION_NAME,
                scroll_filter=filter_conditions,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            # Group by document_id to get unique documents
            documents = {}
            for point in search_result[0]:
                doc_id = point.payload["document_id"]
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "metadata": point.payload["metadata"],
                        "chunk_count": 1,
                        "last_updated": point.payload["metadata"].get("embedding_timestamp")
                    }
                else:
                    documents[doc_id]["chunk_count"] += 1

            return {
                "documents": list(documents.values()),
                "total": len(documents),
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise Exception(f"Error listing documents: {str(e)}")

    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            # Create filter for the document ID
            filter_conditions = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=Match(
                            value=document_id
                        )
                    )
                ]
            )
            
            # Delete all points for this document
            self.client.delete(
                collection_name=self.settings.COLLECTION_NAME,
                points_selector=filter_conditions
            )
            
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")

    async def get_document_metadata(
        self, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific document"""
        try:
            filter_conditions = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=Match(value=document_id)
                    )
                ]
            )
            
            search_result = self.client.scroll(
                collection_name=self.settings.COLLECTION_NAME,
                scroll_filter=filter_conditions,
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            if search_result[0]:
                return search_result[0][0].payload["metadata"]
            return None
            
        except Exception as e:
            logger.error(f"Error getting document metadata: {str(e)}")
            raise Exception(f"Error getting document metadata: {str(e)}")