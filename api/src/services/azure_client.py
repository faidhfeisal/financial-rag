from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncAzureOpenAI
import logging
import aiohttp
import json
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError
from datetime import datetime
import os

logger = logging.getLogger(__name__)
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class AzureClient:
    def __init__(self):
        self.settings = get_settings()
        
        # Store credentials
        self.api_key = self.settings.AZURE_OPENAI_API_KEY
        self.endpoint = self.settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
        self.deployment = self.settings.AZURE_EMBEDDING_DEPLOYMENT_NAME
        self.api_version = "2024-02-15-preview"

        # Initialize blob storage client
        self.blob_service = BlobServiceClient.from_connection_string(
            self.settings.AZURE_STORAGE_CONNECTION_STRING
        )

        logger.info(f"Initializing with endpoint: {self.endpoint}")
        logger.info(f"Using deployment: {self.deployment}")

        logger.info(f"Initializing with endpoint: {self.endpoint}")
        logger.info(f"Using deployment: {self.deployment}")
        logger.info(f"Using API KEY: {self.api_key}")

        try:
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint
            )
            logger.info("Azure OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

    async def store_document(
        self,
        content: bytes,
        filename: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Store a document in Azure Blob Storage
        
        Args:
            content: Document content as bytes
            filename: Name of the file to store
            metadata: Document metadata
            
        Returns:
            URL of the stored document or None if storage fails
        """
        try:
            # Ensure container exists
            container_client = self.blob_service.get_container_client(
                self.settings.DOCUMENTS_CONTAINER_NAME
            )
            
            # Create container if it doesn't exist
            if not container_client.exists():
                container_client.create_container()

            # Generate blob name with timestamp to avoid conflicts
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"{timestamp}_{filename}"

            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)

            # Set content settings for the blob
            content_settings = ContentSettings(
                content_type='text/plain',
                content_encoding='utf-8'
            )

            # Convert metadata values to strings
            string_metadata = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in metadata.items()
            }

            # Upload the document
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=content_settings,
                metadata=string_metadata
            )

            logger.info(f"Successfully stored document: {blob_name}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Error storing document in blob storage: {str(e)}")
            raise Exception(f"Failed to store document: {str(e)}")

    async def store_json(self, container_name: str, blob_name: str, data: Dict[str, Any]) -> Optional[str]:
        """Store JSON data in Azure Blob Storage"""
        try:
            # Create container if it doesn't exist
            container_client = self.blob_service.get_container_client(container_name)
            
            if not container_client.exists():
                container_client.create_container()

            # Convert data to JSON string
            json_data = json.dumps(data, default=str).encode('utf-8')

            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Set content settings
            content_settings = ContentSettings(
                content_type='application/json',
                content_encoding='utf-8'
            )
            
            # Upload synchronously (blob storage SDK doesn't support async)
            blob_client.upload_blob(
                json_data,
                overwrite=True,
                content_settings=content_settings
            )

            logger.info(f"Successfully stored JSON data to {container_name}/{blob_name}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Error storing JSON data: {str(e)}")
            return None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using direct API call"""
        try:
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/embeddings?api-version={self.api_version}"
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "input": text,
                "model": self.deployment
            }

            logger.info(f"Making embedding request to: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['data'][0]['embedding']
                    else:
                        error_text = await response.text()
                        logger.error(f"Embedding request failed with status {response.status}: {error_text}")
                        raise Exception(f"Embedding request failed: {error_text}")

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise Exception(f"Error generating embedding: {str(e)}")

    async def generate_completion(
        self,
        query: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate completion using direct API call"""
        try:
            url = f"{self.endpoint}/openai/deployments/{self.settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={self.api_version}"
            
            # Prepare context from retrieved documents
            context_text = "\n".join(
                f"Document {i+1}:\n{doc['content']}"
                for i, doc in enumerate(context)
            )
            
            # Construct the prompt
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate information about financial regulations."
                },
                {
                    "role": "user",
                    "content": f"""Use the following documents to answer the question. Include citations [1], [2], etc.
                    If the answer cannot be found in the documents, say so.

                    Documents:
                    {context_text}

                    Question: {query}

                    Answer:"""
                }
            ]

            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": messages,
                "temperature": 0,
                "max_tokens": 500,
                "model": self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "text": result['choices'][0]['message']['content'],
                            "usage": result['usage']
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Completion request failed with status {response.status}: {error_text}")
                        raise Exception(f"Completion request failed: {error_text}")

        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            raise Exception(f"Error generating completion: {str(e)}")

    async def test_connection(self) -> bool:
        """Test the connection to Azure OpenAI"""
        try:
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/embeddings?api-version={self.api_version}"
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "input": "test",
                "model": self.deployment
            }

            logger.info(f"Testing connection to: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        logger.info("Connection test successful")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Connection test failed with status {response.status}: {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
        
    async def store_json(self, container_name: str, blob_name: str, data: Dict[str, Any]) -> Optional[str]:
        """Store JSON data in Azure Blob Storage"""
        try:
            # Create container if it doesn't exist
            container_client = self.blob_service.get_container_client(container_name)
            
            # Create container if it doesn't exist
            if not container_client.exists():
                container_client.create_container()

            # Convert data to JSON string
            json_data = json.dumps(data, default=str).encode('utf-8')

            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Upload synchronously (blob storage SDK doesn't support async)
            blob_client.upload_blob(json_data, overwrite=True)

            logger.info(f"Successfully stored JSON data to {container_name}/{blob_name}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Error storing JSON data: {str(e)}")
            return None
        
    async def generate_completion_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0
    ) -> AsyncGenerator[str, None]:
        """Generate streaming completion using direct API call"""
        try:
            url = f"{self.endpoint}/openai/deployments/{self.settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={self.api_version}"
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides accurate information about financial regulations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                "model": self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
            }

            logger.info(f"Starting completion stream with prompt: {prompt[:100]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Streaming request failed with status {response.status}: {error_text}")
                        raise Exception(f"Streaming request failed: {error_text}")
                    
                    # Process the streaming response
                    async for line in response.content:
                        if not line:
                            continue
                            
                        line = line.decode('utf-8').strip()
                        if not line or not line.startswith('data: '):
                            continue
                            
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                            
                        try:
                            response_data = json.loads(data)
                            if content := response_data.get('choices', [{}])[0].get('delta', {}).get('content'):
                                logger.info(f"Yielding content: {content}")
                                yield content
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode JSON: {e}, data: {data}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing stream chunk: {str(e)}")
                            continue

        except Exception as e:
            logger.error(f"Error in streaming completion: {str(e)}")
            raise Exception(f"Error in streaming completion: {str(e)}")