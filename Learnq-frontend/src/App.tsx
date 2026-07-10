import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/common/Navbar';
import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import HistoryPage from './pages/history/HistoryPage';
import HistoryDetailsPage from './pages/history/HistoryDetailsPage';
import './App.css';

import AuthAlert from './components/common/AuthAlert';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const hideNavbar = ['/login', '/signup', '/'].includes(location.pathname);

  return (
    <>
      {!hideNavbar && <Navbar />}
      <div style={{ paddingTop: hideNavbar ? '0' : '80px' }}>
        {children}
      </div>
    </>
  );
};

function App() {
  const [showAuthAlert, setShowAuthAlert] = useState(false);

  useEffect(() => {
    const handleTokenExpiration = () => {
      setShowAuthAlert(true);
    };

    window.addEventListener('token-expired', handleTokenExpiration);
    return () => window.removeEventListener('token-expired', handleTokenExpiration);
  }, []);

  return (
    <Router>
      <Layout>
        {showAuthAlert && <AuthAlert onClose={() => setShowAuthAlert(false)} />}
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:id" element={<HistoryDetailsPage />} />
          {/* Placeholder for dashboard */}
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App
