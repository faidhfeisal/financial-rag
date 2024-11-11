const BASE_URL = 'http://127.0.0.1:8000/api/v1';

async function getAuthHeaders() {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('Not authenticated');
  
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

export const api = {
  async query(text) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${BASE_URL}/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query: text })
    });
    
    if (!response.ok) throw new Error('Query failed');
    return response.json();
  },

  async streamQuery(text) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${BASE_URL}/query/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query: text })
    });
    
    if (!response.ok) throw new Error('Query stream failed');
    return response;
  },

  async uploadDocument(file, metadata) {
    const headers = await getAuthHeaders();
    delete headers['Content-Type']; // Let browser set for FormData
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await fetch(`${BASE_URL}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },

  async listDocuments() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${BASE_URL}/documents`, {
      headers
    });

    if (!response.ok) throw new Error('Failed to fetch documents');
    return response.json();
  },

  async deleteDocument(documentId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${BASE_URL}/documents/${documentId}`, {
        method: 'DELETE',
        headers
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Delete failed');
    }

    return response.json();
}
};