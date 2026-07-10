import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaGoogle, FaGithub, FaEnvelope, FaLock } from 'react-icons/fa';
import AuthLayout from './AuthLayout';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import { authService } from '../../services/api';
import '../../assets/styles/LoginPage.css';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await authService.login({
        email: formData.email,
        password: formData.password
      });
      // Navigate to dashboard on success
      navigate('/dashboard'); 
    } catch (err: any) {
      console.error('Login failed:', err);
      setError(err.response?.data?.detail || 'Failed to login. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout 
      title="Welcome Back" 
      subtitle="Sign in to continue your transcription journey"
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="alert alert-danger p-2 mb-3 small" role="alert">
            {error}
          </div>
        )}
        <Input
          label="Email Address"
          id="email"
          name="email"
          type="email"
          placeholder="name@example.com"
          value={formData.email}
          onChange={handleChange}
          required
          icon={<FaEnvelope/>}
        />
        
        <Input
          label="Password"
          id="password"
          name="password"
          type="password"
          placeholder="••••••••"
          value={formData.password}
          onChange={handleChange}
          required
          icon={<FaLock />}
        />

        <div className="d-flex justify-content-between align-items-center mb-4">
          <div className="form-check">
            <input className="form-check-input bg-transparent" type="checkbox" id="rememberMe" />
            <label className="form-check-label text-secondary small" htmlFor="rememberMe">
              Remember me
            </label>
          </div>
          <a href="#" className="text-decoration-none small text-primary">
            Forgot Password?
          </a>
        </div>

        <Button type="submit" isLoading={loading}>
          Sign In
        </Button>

        <div className="social-login">
          <button type="button" className="social-btn" title="Sign in with Google">
            <FaGoogle />
          </button>
          <button type="button" className="social-btn" title="Sign in with Github">
            <FaGithub />
          </button>
        </div>

        <div className="auth-footer">
          Don't have an account?{' '}
          <Link to="/signup" className="auth-link">
            Sign up
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};

export default LoginPage;
