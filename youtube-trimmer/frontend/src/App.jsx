import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import SimpleDashboard from './components/SimpleDashboard';
import SimpleLandingPage from './components/SimpleLandingPage';

// Import our professional design system
import './styles/design-system.css';
import './styles/reely-colors.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div style={{ minHeight: '100vh' }}>
          <Routes>
            <Route path="/" element={<SimpleLandingPage />} />
            <Route path="/dashboard" element={<SimpleDashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;