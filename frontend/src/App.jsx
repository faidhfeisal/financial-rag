import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import RAGInterface from './components/RAGInterface';

function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <RAGInterface />
      </ProtectedRoute>
    </AuthProvider>
  );
}

export default App;