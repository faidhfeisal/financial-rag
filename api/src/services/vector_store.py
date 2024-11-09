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
        collections = self.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if self.settings.COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=self.settings.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.settings.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    async def store_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store document chunks with their embeddings"""
        try:
            points = []
            for i, chunk in enumerate(chunks):
                point = PointStruct(
                    id=f"{metadata['document_id']}_{i}",
                    vector=chunk["embedding"],
                    payload={
                        "document_id": metadata["document_id"],
                        "content": chunk["content"],
                        "metadata": metadata,
                        "chunk_index": i
                    }
                )
                points.append(point)

            self.client.upsert(
                collection_name=self.settings.COLLECTION_NAME,
                points=points
            )
            return True
        except Exception as e:
            raise Exception(f"Error storing embeddings: {str(e)}")

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
                        # Handle array filters (like tags)
                        conditions.append(
                            FieldCondition(
                                key=f"metadata.{key}",
                                match=Match(
                                    any=value
                                )
                            )
                        )
                    else:
                        conditions.append(
                            FieldCondition(
                                key=f"metadata.{key}",
                                match=Match(
                                    value=value
                                )
                            )
                        )
                filter_conditions = Filter(
                    must=conditions
                )

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
                        "chunk_count": 1
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

    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific document"""
        try:
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
            raise Exception(f"Error getting document metadata: {str(e)}")