import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Login from './Login';

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();

  if (!user) {
    return <Login />;
  }

  return children;
}