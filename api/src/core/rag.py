from typing import Dict, Any, List, AsyncGenerator, Optional
from datetime import datetime
import logging
from .config import get_settings
from ..services.azure_client import AzureClient
from ..services.vector_store import VectorStore
from ..services.evaluation import ResponseEvaluation

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        self.settings = get_settings()
        self.azure_client = AzureClient()
        self.vector_store = VectorStore()
        self.evaluator = ResponseEvaluation()

    async def process_query_stream(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using RAG with streaming response"""
        try:
            start_time = datetime.utcnow()
            query_id = f"query_{start_time.timestamp()}"
            
            # Add filters if provided
            filters = filters or {}
            
            # Generate query embedding
            query_embedding = await self.azure_client.generate_embedding(query)
            
            # Retrieve relevant documents
            relevant_docs = await self.vector_store.search_similar(
                query_embedding,
                filters
            )
            
            if not relevant_docs:
                yield {
                    "type": "error",
                    "data": "No relevant information found."
                }
                return

            # Send retrieved sources first
            yield {
                "type": "sources",
                "data": relevant_docs
            }

            # Prepare the context from retrieved documents
            context_text = "\n".join(
                f"Document {i+1}:\n{doc['content']}"
                for i, doc in enumerate(relevant_docs)
            )
            
            # Construct the prompt
            prompt = f"""Use the following documents to answer the question. Include citations [1], [2], etc.
            If the answer cannot be found in the documents, say so.

            Documents:
            {context_text}

            Question: {query}

            Answer:"""

            logger.info("Starting token generation...")
            token_count = 0
            # Generate and stream the response tokens
            async for token in self.azure_client.generate_completion_stream(prompt):
                token_count += 1
                logger.info(f"Sending token {token_count}: {token}")
                yield {
                    "type": "token",
                    "data": token
                }

            # Calculate final metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate confidence
            confidence = sum(doc["similarity"] for doc in relevant_docs) / len(relevant_docs)
            
            # Send final metadata
            yield {
                "type": "metadata",
                "data": {
                    "query_id": query_id,
                    "confidence": confidence,
                    "response_time": execution_time * 1000,  # Convert to ms
                    "sources_count": len(relevant_docs),
                    "token_count": token_count
                }
            }

        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            yield {
                "type": "error",
                "data": str(e)
            }

    async def process_query(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a query using RAG"""
        try:
            start_time = datetime.utcnow()
            query_id = f"query_{start_time.timestamp()}"
            
            # Add filters if provided
            filters = filters or {}
            
            # Generate query embedding
            query_embedding = await self.azure_client.generate_embedding(query)
            
            # Retrieve relevant documents
            relevant_docs = await self.vector_store.search_similar(
                query_embedding,
                filters
            )
            
            if not relevant_docs:
                raise Exception("No relevant information found")

            # Generate completion
            completion = await self.azure_client.generate_completion(
                query=query,
                context=relevant_docs
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Evaluate response
            evaluation = await self.evaluator.evaluate_response(
                query=query,
                response=completion["text"],
                sources=relevant_docs,
                execution_time=execution_time,
                token_usage=completion["usage"]
            )
            
            # Calculate confidence
            confidence = sum(doc["similarity"] for doc in relevant_docs) / len(relevant_docs)
            
            return {
                "query_id": query_id,
                "response": completion["text"],
                "sources": relevant_docs,
                "evaluation": evaluation,
                "usage": completion["usage"],
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise

    async def ingest_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Ingest a document into the RAG system"""
        try:
            logger.info(f"Starting document ingestion: {metadata.get('title', 'Untitled')}")
            
            # Store document in Blob Storage
            doc_url = await self.azure_client.store_document(
                content.encode('utf-8'),
                f"{metadata['document_id']}.txt",
                metadata
            )
            
            # Split into chunks
            chunks = self._chunk_text(content)
            logger.info(f"Created {len(chunks)} chunks from document")
            
            # Generate embeddings for chunks
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self.azure_client.generate_embedding(chunk)
                    chunk_embeddings.append({
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": {
                            **metadata,
                            "chunk_index": i,
                            "chunk_total": len(chunks)
                        }
                    })
                except Exception as e:
                    logger.error(f"Error generating embedding for chunk {i}: {str(e)}")
                    continue
            
            if not chunk_embeddings:
                raise Exception("Failed to generate any valid embeddings")
            
            # Store in vector database
            logger.info("Storing embeddings in vector database")
            await self.vector_store.store_embeddings(
                chunk_embeddings,
                metadata
            )
            
            return {
                "document_id": metadata["document_id"],
                "url": doc_url,
                "chunk_count": len(chunks),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error ingesting document: {str(e)}")
            raise

    async def list_documents(
        self,
        document_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """List available documents"""
        try:
            # Add filters based on document_type and tag
            filters = {}
            if document_type:
                filters["document_type"] = document_type
            if tag:
                filters["tags"] = tag

            result = await self.vector_store.list_documents(
                filters=filters,
                limit=limit,
                offset=offset
            )

            # Add blob storage info if available
            container_client = self.azure_client.blob_service.get_container_client(
                self.settings.DOCUMENTS_CONTAINER_NAME
            )
            
            for doc in result["documents"]:
                blob_name = f"{doc['document_id']}.txt"
                try:
                    blob_client = container_client.get_blob_client(blob_name)
                    properties = blob_client.get_blob_properties()
                    doc["size"] = properties.size
                    doc["last_modified"] = properties.last_modified.isoformat()
                except:
                    # Skip if blob not found
                    pass

            return result

        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise

    async def delete_document(
        self,
        document_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete a document"""
        try:
            # Delete from vector store
            await self.vector_store.delete_document(document_id)
            
            # Delete from blob storage
            container_client = self.azure_client.blob_service.get_container_client(
                self.settings.DOCUMENTS_CONTAINER_NAME
            )
            blob_client = container_client.get_blob_client(f"{document_id}.txt")
            blob_client.delete_blob()
            
            return {
                "status": "success",
                "document_id": document_id
            }

        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        chunks = []
        length = len(text)
        start = 0
        
        while start < length:
            end = start + self.settings.CHUNK_SIZE
            
            if end < length:
                # Find a natural break point
                while end > start and not text[end].isspace():
                    end -= 1
                if end == start:
                    end = start + self.settings.CHUNK_SIZE
            else:
                end = length
            
            chunks.append(text[start:end].strip())
            start = end - self.settings.CHUNK_OVERLAP
            
        return chunks