import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaGoogle, FaGithub, FaUser, FaEnvelope, FaLock, FaIdCard } from 'react-icons/fa';
import { authService } from '../../services/api';
import AuthLayout from './AuthLayout';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';

const SignupPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      await authService.signup({
        email: formData.email,
        name: formData.fullName,
        role: formData.role,
        password: formData.password
      });
      navigate('/login');
    } catch (err: any) {
      console.error('Signup failed:', err);
      setError(err.response?.data?.detail || 'Failed to create account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout 
      title="Create Account" 
      subtitle="Join us and start transcribing your content"
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="alert alert-danger p-2 mb-3 small" role="alert">
            {error}
          </div>
        )}
        <Input
          label="Full Name"
          id="fullName"
          name="fullName"
          type="text"
          placeholder="John Doe"
          value={formData.fullName}
          onChange={handleChange}
          required
          icon={<FaUser />}
        />

        <Input
          label="Role"
          id="role"
          name="role"
          type="text"
          placeholder="Student/Teacher"
          value={formData.role}
          onChange={handleChange}
          required
          icon={<FaIdCard />}
        />

        <Input
          label="Email Address"
          id="email"
          name="email"
          type="email"
          placeholder="name@example.com"
          value={formData.email}
          onChange={handleChange}
          required
          icon={<FaEnvelope />}
        />
        
        <Input
          label="Password"
          id="password"
          name="password"
          type="password"
          placeholder="Create a strong password"
          value={formData.password}
          onChange={handleChange}
          required
          icon={<FaLock />}
        />

        <Input
          label="Confirm Password"
          id="confirmPassword"
          name="confirmPassword"
          type="password"
          placeholder="Confirm your password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          icon={<FaLock />}
        />

        
        <Button type="submit" isLoading={loading}>
          Create Account
        </Button>

        <div className="social-login">
            <button type="button" className="social-btn" title="Sign up with Google">
            <FaGoogle />
          </button>
          <button type="button" className="social-btn" title="Sign up with Github">
            <FaGithub />
          </button>
        </div>

        <div className="auth-footer">
          Already have an account?{' '}
          <Link to="/login" className="auth-link">
            Log in
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};

export default SignupPage;
