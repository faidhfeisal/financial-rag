import pytest
from .test_rag_system import login

@pytest.mark.asyncio
async def test_various_queries(http_session):
    """Test different types of queries"""
    queries = [
        # Direct questions
        {
            "query": "What are the key requirements for access control in ISO 27001?",
            "expected_sources": ["ISO27001_Security_Guidelines.txt"],
            "expected_keywords": ["RBAC", "access", "password"]
        },
        # Cross-document questions
        {
            "query": "How do security requirements relate to financial messaging?",
            "expected_sources": ["ISO27001_Security_Guidelines.txt", "ISO20022_Financial_Messaging.txt"],
            "expected_keywords": ["security", "message"]
        },
        # Specific technical questions
        {
            "query": "What message type is used for Customer Credit Transfer?",
            "expected_sources": ["ISO20022_Financial_Messaging.txt"],
            "expected_keywords": ["pacs.008", "Credit Transfer"]
        },
        # Policy questions
        {
            "query": "Explain the encryption requirements for ISO 27001",
            "expected_sources": ["ISO27001_Security_Guidelines.txt"],
            "expected_keywords": ["encryption", "cryptography", "algorithms"]
        }
    ]

    admin_auth = await login(http_session, "admin")
    admin_token = admin_auth["access_token"]

    for query_test in queries:
        async with http_session.post(
            f"{BASE_URL}/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"query": query_test["query"]}
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Check if response contains expected keywords
            assert any(keyword.lower() in data["response"].lower() 
                     for keyword in query_test["expected_keywords"])
            
            # Check if correct sources were used
            source_docs = [source["metadata"]["title"] 
                         for source in data["sources"]]
            assert any(expected in source_docs 
                     for expected in query_test["expected_sources"])

            # Check confidence score
            assert data["confidence"] > 0.7

            # Check for citations
            assert "[" in data["response"] and "]" in data["response"]