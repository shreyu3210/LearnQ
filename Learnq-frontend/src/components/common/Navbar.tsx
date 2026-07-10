import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../../services/api';
import '../../assets/styles/Navbar.css';

const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check auth state on mount, when location changes, or when auth event occurs
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('token');
      setIsAuthenticated(!!token);
    };

    checkAuth();

    window.addEventListener('auth-change', checkAuth);
    // Keep location check as backup
    
    return () => {
      window.removeEventListener('auth-change', checkAuth);
    };
  }, [location]);

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    navigate('/login');
  };

  return (
    <nav className="navbar-custom">
      <Link to="/dashboard" className="navbar-brand">
        LearnQ
      </Link>
      
      <div className="navbar-nav">
        {isAuthenticated ? (
          <>
            <Link 
              to="/history" 
              className={`nav-link ${location.pathname === '/history' ? 'active' : ''}`}
            >
              History
            </Link>
            <button onClick={handleLogout} className="btn-logout">
              Logout
            </button>
          </>
        ) : (
          <Link to="/login" className="btn-login-nav">
            Login
          </Link>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
