# Financial Regulations RAG Assistant

A Retrieval-Augmented Generation (RAG) system built for financial institutions to efficiently query and retrieve information from regulatory documents and internal knowledge bases.

## 🌟 Features

### Core Functionality
- **RAG Pipeline**: Advanced document retrieval and response generation
- **Real-time Processing**: Streaming responses with live updates
- **Document Management**: Upload, index, and manage regulatory documents
- **Smart Retrieval**: Context-aware document retrieval with similarity scoring
- **Source Attribution**: Automatic citation and source referencing

### Security
- Role-based access control (RBAC)
- Document-level permissions
- Audit logging
- Secure document storage
- Azure AD integration ready

### User Experience
- Intuitive chat interface
- Real-time response streaming
- Interactive source exploration
- Document management dashboard
- Responsive design

## 🏗 Architecture

### Technology Stack
- **Frontend**: React, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python 3.9+
- **AI/ML**: Azure OpenAI, Text Analytics
- **Database**: 
  - Vector Store: Qdrant
  - Cache: Redis
  - Storage: Azure Blob Storage
- **Infrastructure**: Azure Cloud Services

### System Components
```plaintext
├── Frontend (React SPA)
│   ├── Chat Interface
│   ├── Document Management
│   ├── User Authentication
│   └── Analytics Dashboard
│
├── Backend (FastAPI)
│   ├── RAG Pipeline
│   ├── Authentication Service
│   ├── Document Service
│   └── Evaluation Service
│
└── Azure Services
    ├── OpenAI
    ├── Blob Storage
    ├── Key Vault
    └── Application Insights
```

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.9+
python --version

# Node.js 16+
node --version

# Docker & Docker Compose
docker --version
docker-compose --version
```

### Environment Setup
1. Clone the repository:
```bash
git clone https://github.com/faidhfeisal/financial-rag.git
cd financial-rag
```

2. Create and configure environment variables:
```bash
# Copy example env files
cp .env.example .env

# Configure your environment variables
# API
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# Frontend
VITE_API_URL=http://localhost:8000
```

3. Start the services:
```bash
# Using Docker Compose
docker-compose up -d

# Or start services individually
# Backend
cd api
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 💻 Usage

### User Roles
- **Admin**: Full system access, document management
- **Analyst**: Document upload, querying
- **User**: Basic querying capabilities

### Basic Operations
```python
# Python API Client Example
from financial_rag import RAGClient

client = RAGClient(api_key="your_api_key")

# Query the system
response = client.query("What are the key requirements for ISO 27001?")

# Upload document
client.upload_document("path/to/doc.pdf", metadata={
    "title": "ISO 27001 Guidelines",
    "type": "regulation"
})
```

### API Endpoints
```plaintext
POST /api/v1/query
GET  /api/v1/documents
POST /api/v1/documents/upload
POST /api/v1/auth/login
```

## 🔍 Evaluation & Metrics

### Response Quality
- Relevance scoring
- Source citation accuracy
- Response completeness
- User feedback metrics

### System Performance
- Response latency
- Token usage
- Retrieval accuracy
- System resource utilization

## 🔒 Security Considerations

### Data Protection
- Encryption at rest and in transit
- Secure document storage
- Access control policies
- Audit logging

### Compliance
- GDPR readiness
- Financial regulations compliance
- Data sovereignty support
- Audit trail maintenance

## 🛠 Development

### Project Structure
```plaintext
.
├── api/
│   ├── src/
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   └── styles/
│   └── package.json
│
└── docker-compose.yml
```

### Testing
```bash
# Backend tests
cd api
pytest

# Frontend tests
cd frontend
npm test
```

## 📈 Monitoring & Maintenance

### System Monitoring
- Application Insights integration
- Performance metrics
- Error tracking
- Usage analytics

### Regular Maintenance
- Document index optimization
- Cache management
- Security updates
- Performance tuning