const BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const api = {
  async query(text) {
    const response = await fetch(`${BASE_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text })
    });
    
    if (!response.ok) throw new Error('Query failed');
    return response.json();
  },

  async submitFeedback(feedback) {
    const response = await fetch(`${BASE_URL}/evaluation/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback)
    });
    
    if (!response.ok) throw new Error('Feedback submission failed');
  }
  async uploadDocument(file, metadata) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await fetch('/api/v1/documents/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },

  async listDocuments() {
    const response = await fetch('/api/v1/documents');
    if (!response.ok) throw new Error('Failed to fetch documents');
    return response.json();
  },

  async deleteDocument(documentId) {
    const response = await fetch(`/api/v1/documents/${documentId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Delete failed');
    return response.json();
  }
};