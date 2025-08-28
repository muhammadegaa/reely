import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Register = () => {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      const result = await register(formData.email, formData.password, formData.fullName);
      if (result.success) {
        navigate('/dashboard');
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--color-gray-50)',
      padding: 'var(--space-5)'
    }}>
      <div className="card" style={{
        padding: 'var(--space-10)',
        width: '100%',
        maxWidth: '480px',
        boxShadow: 'var(--shadow-xl)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <Link to="/" className="nav-brand" style={{ 
            color: 'var(--color-primary-600)', 
            textDecoration: 'none',
            fontSize: 'var(--text-2xl)',
            justifyContent: 'center',
            marginBottom: 'var(--space-4)'
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
            Reely
          </Link>
          <h1 className="text-2xl font-bold text-gray-900" style={{ marginBottom: 'var(--space-2)' }}>
            Create your account
          </h1>
          <p className="text-gray-600">
            Start creating viral content in under 60 seconds
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">
              Full name
            </label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              required
              className="form-input"
              placeholder="Enter your full name"
              autoComplete="name"
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Email address
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="form-input"
              placeholder="Enter your email"
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              className="form-input"
              placeholder="Create a password"
              autoComplete="new-password"
            />
            <p className="text-xs text-gray-500" style={{ marginTop: 'var(--space-1)' }}>
              Must be at least 8 characters long
            </p>
          </div>

          <div className="form-group">
            <label className="form-label">
              Confirm password
            </label>
            <input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              className="form-input"
              placeholder="Confirm your password"
              autoComplete="new-password"
            />
          </div>

          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-lg"
            style={{ width: '100%', justifyContent: 'center', marginBottom: 'var(--space-6)' }}
          >
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <div className="loading-spinner" style={{ width: '16px', height: '16px' }} />
                Creating account...
              </div>
            ) : (
              'Create account'
            )}
          </button>

          <p className="text-xs text-gray-500 text-center" style={{ lineHeight: 'var(--leading-relaxed)' }}>
            By creating an account, you agree to our{' '}
            <Link to="#" className="text-primary-600" style={{ textDecoration: 'none' }}>Terms of Service</Link>
            {' '}and{' '}
            <Link to="#" className="text-primary-600" style={{ textDecoration: 'none' }}>Privacy Policy</Link>
          </p>
        </form>

        <div style={{
          marginTop: 'var(--space-8)',
          textAlign: 'center',
          paddingTop: 'var(--space-6)',
          borderTop: '1px solid var(--color-gray-200)'
        }}>
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <Link 
              to="/login" 
              className="text-primary-600 font-medium"
              style={{ textDecoration: 'none' }}
            >
              Sign in
            </Link>
          </p>
        </div>

        <div className="card" style={{
          marginTop: 'var(--space-6)',
          padding: 'var(--space-5)',
          backgroundColor: 'var(--color-primary-50)',
          border: '1px solid var(--color-primary-200)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style={{ color: 'var(--color-primary-600)' }}>
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 11 1.16-.21 2.31-.48 3.38-.84"/>
              <path d="M22 12c0 5.55-3.84 10-9 11"/>
              <path d="M8 11l4 4 8-8"/>
            </svg>
            <h4 className="font-semibold text-primary-900">
              Free plan includes:
            </h4>
          </div>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(2, 1fr)', 
            gap: 'var(--space-2)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-primary-700)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
              </svg>
              5 video trims/month
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
              </svg>
              AI hook detection
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
              </svg>
              Mobile formatting
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
              </svg>
              Auto subtitles
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;