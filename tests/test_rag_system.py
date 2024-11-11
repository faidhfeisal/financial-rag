import pytest
import aiohttp
from typing import Dict, Any
import json

BASE_URL = "http://localhost:8000/api/v1"

# Test users
USERS = {
    "admin": {
        "email": "admin@example.com",
        "password": "admin123"
    },
    "analyst": {
        "email": "analyst@example.com",
        "password": "analyst123"
    },
    "user": {
        "email": "user@example.com",
        "password": "user123"
    }
}

async def login(session: aiohttp.ClientSession, user_type: str) -> Dict[str, Any]:
    """Login and get token"""
    credentials = USERS[user_type]
    async with session.post(
        f"{BASE_URL}/auth/login",
        json=credentials
    ) as response:
        assert response.status == 200
        data = await response.json()
        return data

async def upload_document(
    session: aiohttp.ClientSession,
    token: str,
    filepath: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Upload a document"""
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(filepath, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file',
                      f,
                      filename=filepath.split('/')[-1],
                      content_type='text/plain')
        data.add_field('metadata', json.dumps(metadata))

        async with session.post(
            f"{BASE_URL}/documents/upload",
            headers=headers,
            data=data
        ) as response:
            return await response.json()

@pytest.mark.asyncio
async def test_user_roles(http_session: aiohttp.ClientSession):
    """Test different user roles and permissions"""
    # Test Admin Role
    admin_auth = await login(http_session, "admin")
    admin_token = admin_auth["access_token"]
    
    # Upload documents as admin
    doc1 = await upload_document(
        http_session,
        admin_token,
        "test_documents/ISO27001_Security_Guidelines.txt",
        {
            "title": "ISO 27001 Guidelines",
            "document_type": "regulation",
            "tags": ["security", "compliance"]
        }
    )
    assert doc1["status"] == "success"

    doc2 = await upload_document(
        http_session,
        admin_token,
        "test_documents/ISO20022_Financial_Messaging.txt",
        {
            "title": "ISO 20022 Guidelines",
            "document_type": "regulation",
            "tags": ["financial", "messaging"]
        }
    )
    assert doc2["status"] == "success"

    # Test document listing for different roles
    async def test_list_documents(token: str):
        async with http_session.get(
            f"{BASE_URL}/documents",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            return await response.json()

    # Admin should see all documents
    admin_docs = await test_list_documents(admin_token)
    assert len(admin_docs["documents"]) == 2

    # Analyst login and document access
    analyst_auth = await login(http_session, "analyst")
    analyst_token = analyst_auth["access_token"]
    analyst_docs = await test_list_documents(analyst_token)
    assert len(analyst_docs["documents"]) == 2

    # Regular user access
    user_auth = await login(http_session, "user")
    user_token = user_auth["access_token"]
    user_docs = await test_list_documents(user_token)
    assert len(user_docs["documents"]) == 2

    # Test querying with different roles
    async def test_query(token: str, query: str):
        async with http_session.post(
            f"{BASE_URL}/query/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query}
        ) as response:
            return response.status == 200

    # Test queries
    queries = [
        "What are the key requirements for access control in ISO 27001?",
        "Explain the message types in ISO 20022",
        "What are the security guidelines for passwords?",
    ]

    for query in queries:
        assert await test_query(admin_token, query)
        assert await test_query(analyst_token, query)
        assert await test_query(user_token, query)

    # Test document deletion (admin only)
    async def test_delete_document(token: str, doc_id: str):
        async with http_session.delete(
            f"{BASE_URL}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            return response.status

    # Admin should be able to delete
    assert await test_delete_document(admin_token, doc1["document_id"]) == 200

    # Analyst should not be able to delete
    assert await test_delete_document(analyst_token, doc2["document_id"]) == 403

@pytest.mark.asyncio
async def test_document_operations(http_session: aiohttp.ClientSession):
    """Test various document operations"""
    admin_auth = await login(http_session, "admin")
    admin_token = admin_auth["access_token"]

    # Test document upload
    doc = await upload_document(
        http_session,
        admin_token,
        "test_documents/ISO27001_Security_Guidelines.txt",
        {
            "title": "ISO 27001 Guidelines",
            "document_type": "regulation",
            "tags": ["security", "compliance"]
        }
    )
    assert doc["status"] == "success"

    # Test querying the document
    async with http_session.post(
        f"{BASE_URL}/query",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "query": "What are the password requirements in ISO 27001?"
        }
    ) as response:
        assert response.status == 200
        response_data = await response.json()
        assert "password" in response_data["response"].lower()
        assert len(response_data["sources"]) > 0