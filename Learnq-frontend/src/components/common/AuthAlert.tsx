import React from 'react';
import '../../assets/styles/AuthAlert.css';
import { FaExclamationTriangle } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

interface AuthAlertProps {
  onClose: () => void;
}

const AuthAlert: React.FC<AuthAlertProps> = ({ onClose }) => {
  const navigate = useNavigate();

  const handleLoginRedirect = () => {
    onClose();
    localStorage.removeItem('token');
    window.dispatchEvent(new Event('auth-change')); // Update Navbar
    navigate('/login');
  };

  return (
    <div className="auth-alert-overlay">
      <div className="auth-alert-card">
        <div className="alert-icon">
          <FaExclamationTriangle />
        </div>
        <h3>Session Expired</h3>
        <p>Your session has expired or is invalid. Please log in again to continue.</p>
        <button onClick={handleLoginRedirect} className="alert-btn">
          Login Again
        </button>
      </div>
    </div>
  );
};

export default AuthAlert;
