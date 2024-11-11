from typing import Dict, Any, List, AsyncGenerator, Optional,  Generator
from datetime import datetime
import logging
from contextlib import contextmanager
import gc
import psutil
import traceback
from .config import get_settings
from ..services.azure_client import AzureClient
from ..services.vector_store import VectorStore
from ..services.evaluation import ResponseEvaluation
from ..utils.exceptions import (
    DocumentProcessingError,
    EmbeddingGenerationError,
    VectorStoreError,
    StorageError
)
import os

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
        """Ingest a document with robust error handling"""
        try:
            # Step 1: Store document
            logger.info(f"Starting document ingestion: {metadata.get('title', 'Untitled')}")
            doc_url = await self.azure_client.store_document(
                content.encode('utf-8'),
                f"{metadata['document_id']}.txt",
                metadata
            )
            logger.info("Document stored successfully")

            # Step 2: Create chunks with defensive handling
            logger.info("Starting text chunking")
            try:
                chunks = self._chunk_text(content)
                if not chunks:
                    raise ValueError("No chunks created")
                logger.info(f"Successfully created {len(chunks)} chunks")
            except Exception as chunk_error:
                logger.error(f"Chunking failed: {str(chunk_error)}")
                # Fallback to single chunk
                chunks = [content.strip()]
                logger.info("Falling back to single chunk")

            # Step 3: Process chunks with individual error handling
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"Processing chunk {i+1}/{len(chunks)}")
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
                    logger.info(f"Successfully processed chunk {i+1}")
                except Exception as embed_error:
                    logger.error(f"Error processing chunk {i+1}: {str(embed_error)}")
                    continue

            if not chunk_embeddings:
                raise ValueError("No embeddings were successfully generated")

            # Step 4: Store embeddings
            logger.info("Storing embeddings in vector store")
            await self.vector_store.store_embeddings(
                chunk_embeddings,
                metadata
            )
            logger.info("Embeddings stored successfully")

            return {
                "document_id": metadata["document_id"],
                "url": doc_url,
                "chunk_count": len(chunks),
                "embedding_count": len(chunk_embeddings),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Document ingestion failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def _cleanup_failed_ingestion(
        self,
        status: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Cleanup any partial uploads in case of failure"""
        try:
            # Only cleanup if document was stored
            if "document_storage" in status["steps_completed"]:
                logger.info(f"Cleaning up stored document: {metadata['document_id']}")
                await self.azure_client.delete_document(metadata["document_id"])

            # Cleanup vector store if embeddings were partially stored
            if "vector_storage" in status["steps_completed"]:
                logger.info(f"Cleaning up vector store entries: {metadata['document_id']}")
                await self.vector_store.delete_document(metadata["document_id"])
                
        except Exception as cleanup_error:
            logger.error(f"Cleanup failed: {str(cleanup_error)}")

    async def get_ingestion_status(
        self,
        process_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the status of a document ingestion process"""
        # Implementation depends on where you store the status
        pass

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
        """Delete a document and all its associated data"""
        logger.info(f"Starting deletion of document: {document_id}")
        
        errors = []
        status = {
            "blob_storage": False,
            "vector_store": False
        }

        # 1. Delete from blob storage
        try:
            container_client = self.azure_client.blob_service.get_container_client(
                self.settings.DOCUMENTS_CONTAINER_NAME
            )
            blob_client = container_client.get_blob_client(f"{document_id}.txt")
            await blob_client.delete_blob()
            status["blob_storage"] = True
            logger.info(f"Deleted document from blob storage: {document_id}")
        except Exception as e:
            errors.append(f"Blob storage deletion failed: {str(e)}")
            logger.error(f"Failed to delete from blob storage: {str(e)}")

        # 2. Delete from vector store
        try:
            await self.vector_store.delete_document(document_id)
            status["vector_store"] = True
            logger.info(f"Deleted document from vector store: {document_id}")
        except Exception as e:
            errors.append(f"Vector store deletion failed: {str(e)}")
            logger.error(f"Failed to delete from vector store: {str(e)}")

        # 3. Delete any cached embeddings
        try:
            await self.embeddings_service.clear_document_cache(document_id)
            logger.info(f"Cleared embeddings cache for document: {document_id}")
        except Exception as e:
            logger.warning(f"Failed to clear embeddings cache: {str(e)}")
            # Non-critical error, don't add to errors list

        # Check if all deletions were successful
        if all(status.values()):
            return {
                "status": "success",
                "document_id": document_id,
                "details": status
            }
        else:
            raise Exception(f"Deletion partially failed: {'; '.join(errors)}")

    @contextmanager
    def _monitor_resources(self, operation: str):
        """Monitor resource usage during operations"""
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            logger.info(f"Starting {operation}. Current memory usage: {start_memory:.2f}MB")
            yield
        finally:
            current_memory = process.memory_info().rss / 1024 / 1024
            logger.info(
                f"Completed {operation}. "
                f"Memory usage: {current_memory:.2f}MB "
                f"(Delta: {(current_memory - start_memory):.2f}MB)"
            )

    def _chunk_text(self, text: str) -> List[str]:
        """Simple and robust text chunking"""
        try:
            logger.info(f"Starting simple chunking for text of length {len(text)}")
            
            # For small documents (< 1000 chars), just create a single chunk
            if len(text) < 1000:
                logger.info("Document is small, creating single chunk")
                return [text.strip()]
            
            # For larger documents, split by paragraphs first
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            logger.info(f"Split into {len(paragraphs)} paragraphs")
            
            chunks = []
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < 1000:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            logger.info(f"Created {len(chunks)} chunks successfully")
            return chunks

        except Exception as e:
            logger.error(f"Chunking failed with error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # For very small documents, return as single chunk as fallback
            if len(text) < 1000:
                logger.info("Fallback: returning entire text as single chunk")
                return [text.strip()]
            raise

    def _chunk_generator(self, text: str) -> Generator[str, None, None]:
        """Generate chunks one at a time to minimize memory usage"""
        length = len(text)
        start = 0
        chunk_size = min(self.settings.CHUNK_SIZE, 1000)  # Limit chunk size
        chunk_overlap = min(self.settings.CHUNK_OVERLAP, 100)  # Limit overlap

        while start < length:
            # Calculate end position
            end = min(start + chunk_size, length)
            
            # Find natural break point if not at the end
            if end < length:
                for char in ['.', '!', '?', '\n', ' ']:
                    pos = text.rfind(char, start, end)
                    if pos != -1:
                        end = pos + 1
                        break

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:  # Only yield non-empty chunks
                yield chunk

            # Move start position
            start = end - chunk_overlap
            if start >= end:
                break

            # Force garbage collection after each chunk
            if start % (chunk_size * 10) == 0:
                gc.collect()