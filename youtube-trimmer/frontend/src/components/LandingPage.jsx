import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const LandingPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header className="nav-header">
        <div className="nav-container">
          <Link to="/" className="nav-brand">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
            Reely
          </Link>

          <div className="nav-menu">
            <Link to="/login" className="btn btn-ghost">
              Sign in
            </Link>
            <Link to="/register" className="btn btn-primary">
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div style={{ maxWidth: '768px', margin: '0 auto' }}>
            <h1 className="text-5xl font-bold text-gray-900 leading-tight" style={{ marginBottom: 'var(--space-6)' }}>
              Turn YouTube videos into 
              <span className="text-primary-600">viral social content</span>
            </h1>
            
            <p className="text-xl text-gray-600 leading-relaxed" style={{ marginBottom: 'var(--space-10)' }}>
              AI-powered video trimming that finds the most engaging moments 
              and converts them to perfect TikTok and Instagram format with 
              automatic subtitles and mobile optimization.
            </p>

            <div style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'center', flexWrap: 'wrap', marginBottom: 'var(--space-12)' }}>
              <Link to="/register" className="btn btn-primary btn-xl">
                Start creating for free
              </Link>
              <a href="#features" className="btn btn-secondary btn-xl">
                Learn more
              </a>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 'var(--space-8)',
              flexWrap: 'wrap',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-gray-500)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                  <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
                </svg>
                No credit card required
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                  <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
                </svg>
                5 free videos monthly
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)' }}>
                  <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
                </svg>
                Setup in 60 seconds
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="section" style={{ backgroundColor: 'white' }}>
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-16)' }}>
            <h2 className="text-4xl font-bold text-gray-900" style={{ marginBottom: 'var(--space-4)' }}>
              Everything you need to create viral content
            </h2>
            <p className="text-lg text-gray-600" style={{ maxWidth: '600px', margin: '0 auto' }}>
              From AI-powered hook detection to perfect social media formatting—all in one platform
            </p>
          </div>

          <div className="features-grid">
            {[
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10 9 11 1.16-.21 2.31-.48 3.38-.84"/>
                    <path d="M22 12c0 5.55-3.84 10-9 11"/>
                    <path d="M8 11l4 4 8-8"/>
                  </svg>
                ),
                title: 'AI Hook Detection',
                description: 'Advanced AI analyzes your content to identify the most engaging moments that drive viral potential.'
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                    <line x1="8" y1="21" x2="16" y2="21"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                ),
                title: 'Mobile-First Format',
                description: 'Automatically converts horizontal videos to 9:16 vertical format optimized for TikTok and Instagram.'
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10,9 9,9 8,9"/>
                  </svg>
                ),
                title: 'Smart Subtitles',
                description: 'AI-generated subtitles with perfect timing and formatting to boost engagement and accessibility.'
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                ),
                title: 'Lightning Fast',
                description: 'Process videos in minutes with our optimized pipeline. No more waiting hours for exports.'
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                ),
                title: 'Professional Quality',
                description: 'High-resolution output with proper encoding that meets all social platform requirements.'
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                  </svg>
                ),
                title: 'Full Control',
                description: 'Manual editing tools, custom timing controls, and format preferences for complete creative control.'
              }
            ].map((feature, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon" style={{ color: 'var(--color-primary-600)' }}>
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900" style={{ marginBottom: 'var(--space-3)' }}>
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="section" style={{ backgroundColor: 'var(--color-gray-50)' }}>
        <div className="container" style={{ maxWidth: '1000px' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-16)' }}>
            <h2 className="text-4xl font-bold text-gray-900" style={{ marginBottom: 'var(--space-4)' }}>
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-gray-600">
              Start free, upgrade when you're ready to scale
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 'var(--space-8)'
          }}>
            {[
              {
                name: 'Free',
                price: '$0',
                period: '/month',
                description: 'Perfect for trying out Reely',
                features: [
                  '5 video trims per month',
                  '3 AI hook detections',
                  'Up to 5-minute videos',
                  'Mobile format optimization',
                  'Basic support'
                ],
                cta: 'Start for free',
                popular: false
              },
              {
                name: 'Pro',
                price: '$19',
                period: '/month',
                description: 'For content creators and businesses',
                features: [
                  '100 video trims per month',
                  '50 AI hook detections',
                  'Up to 30-minute videos',
                  'All format options',
                  'API access',
                  'Priority support'
                ],
                cta: 'Start free trial',
                popular: true
              },
              {
                name: 'Enterprise',
                price: '$99',
                period: '/month',
                description: 'For teams and agencies',
                features: [
                  'Unlimited video processing',
                  'Advanced AI features',
                  'Custom integrations',
                  'Team collaboration',
                  'White-label options',
                  'Dedicated support'
                ],
                cta: 'Contact sales',
                popular: false
              }
            ].map((plan, index) => (
              <div key={index} className="card" style={{
                position: 'relative',
                ...(plan.popular ? {
                  border: '2px solid var(--color-primary-500)',
                  boxShadow: 'var(--shadow-xl)'
                } : {})
              }}>
                {plan.popular && (
                  <div style={{
                    position: 'absolute',
                    top: '-10px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    padding: 'var(--space-1) var(--space-3)',
                    backgroundColor: 'var(--color-primary-600)',
                    color: 'white',
                    borderRadius: 'var(--radius-full)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 'var(--font-semibold)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Most Popular
                  </div>
                )}

                <div className="card-body">
                  <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
                    <h3 className="text-xl font-semibold text-gray-900" style={{ marginBottom: 'var(--space-2)' }}>
                      {plan.name}
                    </h3>
                    <p className="text-sm text-gray-600" style={{ marginBottom: 'var(--space-6)' }}>
                      {plan.description}
                    </p>
                    
                    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 'var(--space-1)' }}>
                      <span className="text-4xl font-bold text-gray-900">
                        {plan.price}
                      </span>
                      <span className="text-gray-500">
                        {plan.period}
                      </span>
                    </div>
                  </div>

                  <ul style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: `0 0 var(--space-8) 0`
                  }}>
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-3)',
                        padding: 'var(--space-2) 0',
                        fontSize: 'var(--text-sm)',
                        color: 'var(--color-gray-700)'
                      }}>
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ color: 'var(--color-success)', flexShrink: 0 }}>
                          <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3-3a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
                        </svg>
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <Link
                    to="/register"
                    className={`btn btn-lg ${plan.popular ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ width: '100%', justifyContent: 'center' }}
                  >
                    {plan.cta}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="section" style={{
        backgroundColor: 'var(--color-gray-900)',
        color: 'white',
        textAlign: 'center'
      }}>
        <div className="container" style={{ maxWidth: '600px' }}>
          <h2 className="text-4xl font-bold" style={{ marginBottom: 'var(--space-6)', color: 'white' }}>
            Ready to create viral content?
          </h2>
          <p className="text-lg" style={{
            marginBottom: 'var(--space-10)',
            color: 'var(--color-gray-300)'
          }}>
            Join thousands of creators using Reely to transform their long-form content 
            into engaging social media clips that drive real results.
          </p>
          <Link to="/register" className="btn btn-primary btn-xl">
            Start creating for free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        backgroundColor: 'var(--color-gray-900)',
        color: 'var(--color-gray-400)',
        padding: 'var(--space-16) 0',
        textAlign: 'center',
        borderTop: '1px solid var(--color-gray-800)'
      }}>
        <div className="container">
          <div style={{ marginBottom: 'var(--space-8)' }}>
            <Link to="/" className="nav-brand" style={{ color: 'var(--color-primary-400)', fontSize: 'var(--text-xl)' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
              Reely
            </Link>
          </div>
          
          <p style={{ marginBottom: 'var(--space-6)', color: 'var(--color-gray-500)' }}>
            Transform YouTube videos into viral social media content with AI
          </p>
          
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 'var(--space-8)',
            marginBottom: 'var(--space-8)',
            fontSize: 'var(--text-sm)'
          }}>
            <a href="#" style={{ color: 'var(--color-gray-500)', textDecoration: 'none' }}>Privacy</a>
            <a href="#" style={{ color: 'var(--color-gray-500)', textDecoration: 'none' }}>Terms</a>
            <a href="#" style={{ color: 'var(--color-gray-500)', textDecoration: 'none' }}>Support</a>
          </div>
          
          <p className="text-sm" style={{ color: 'var(--color-gray-600)' }}>
            © 2024 Reely. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;