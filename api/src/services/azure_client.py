from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
import logging
import aiohttp
import json
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from datetime import datetime

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