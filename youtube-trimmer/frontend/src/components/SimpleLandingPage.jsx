import React from 'react';
import { Link } from 'react-router-dom';

const SimpleLandingPage = () => {
  React.useEffect(() => {
    // Import Inter font for professional typography
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
    
    return () => {
      if (document.head.contains(link)) {
        document.head.removeChild(link);
      }
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Navigation Header */}
      <header className="nav-header">
        <div className="nav-container">
          <Link to="/" className="nav-brand">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5,3 19,12 5,21 5,3"/>
            </svg>
            Reely
          </Link>

          <div className="nav-menu">
            <Link to="/dashboard" className="btn btn-primary">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <div className="text-center" style={{ marginBottom: 'var(--space-12)' }}>
              <h1 className="text-6xl font-bold text-gray-900" style={{ 
                lineHeight: '1.1', 
                marginBottom: 'var(--space-6)',
                letterSpacing: '-0.02em'
              }}>
                Transform YouTube videos into 
                <span className="text-accent"> viral clips</span>
              </h1>
              
              <p className="text-xl text-gray-600 max-w-2xl mx-auto" style={{ 
                marginBottom: 'var(--space-10)',
                lineHeight: '1.6'
              }}>
                AI-powered video processing that identifies the most engaging moments 
                and converts them to optimized social media format with automatic subtitles
              </p>

              <div className="hero-cta">
                <Link to="/dashboard" className="btn btn-primary btn-xl">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5,3 19,12 5,21 5,3"/>
                  </svg>
                  Start Processing
                </Link>
                <p className="text-sm text-muted" style={{ marginTop: 'var(--space-2)' }}>
                  Free demo • No signup required • Enterprise ready
                </p>
              </div>
            </div>

            {/* Performance Stats */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-number">95%</div>
                <div className="stat-label">Faster processing</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">15-30s</div>
                <div className="stat-label">Optimal clip length</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">9:16</div>
                <div className="stat-label">Mobile-first format</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section style={{ 
        padding: 'var(--space-32) 0',
        backgroundColor: 'var(--color-gray-50)'
      }}>
        <div className="container">
          <div className="text-center" style={{ marginBottom: 'var(--space-20)' }}>
            <h2 className="text-4xl font-bold text-gray-900" style={{ 
              marginBottom: 'var(--space-6)',
              letterSpacing: '-0.02em'
            }}>
              Enterprise-grade video processing
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Professional tools that scale with your content operations and maximize ROI.
            </p>
          </div>

          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
              </div>
              <h3 className="feature-title">AI Content Analysis</h3>
              <p className="feature-description">
                Machine learning algorithms analyze engagement patterns to identify 
                high-performing segments that drive conversion and retention.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="2" y="4" width="20" height="16" rx="2"/>
                  <path d="M8 12l5-3v6l-5-3z"/>
                </svg>
              </div>
              <h3 className="feature-title">Automated Format Optimization</h3>
              <p className="feature-description">
                Intelligent aspect ratio conversion with advanced cropping algorithms 
                and background enhancement for maximum platform compatibility.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  <path d="M8 9h8"/>
                  <path d="M8 13h6"/>
                </svg>
              </div>
              <h3 className="feature-title">Automated Transcription</h3>
              <p className="feature-description">
                Production-ready subtitle generation with customizable styling, 
                improving accessibility and engagement metrics across platforms.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Section */}
      <section className="section-dark" style={{ 
        padding: 'var(--space-32) 0'
      }}>
        <div className="container">
          <div className="text-center">
            <h2 className="text-4xl font-bold" style={{ 
              marginBottom: 'var(--space-6)',
              letterSpacing: '-0.02em'
            }}>
              Scale your content operations
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto" style={{ 
              marginBottom: 'var(--space-10)',
              lineHeight: '1.6'
            }}>
              Join enterprise teams who have accelerated their content workflows 
              with automated video processing and optimization.
            </p>
            
            <div className="hero-cta">
              <Link to="/dashboard" className="btn btn-primary btn-xl">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5,3 19,12 5,21 5,3"/>
                </svg>
                Start Free Trial
              </Link>
              <p className="text-sm text-gray-500" style={{ marginTop: 'var(--space-2)' }}>
                No credit card required • Enterprise ready • SOC 2 compliant
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ 
        backgroundColor: 'var(--color-gray-100)',
        padding: 'var(--space-16) 0',
        borderTop: '1px solid var(--color-gray-200)'
      }}>
        <div className="container">
          <div className="text-center">
            <div className="nav-brand" style={{ 
              justifyContent: 'center',
              marginBottom: 'var(--space-6)',
              color: 'var(--color-accent)',
              cursor: 'default'
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5,3 19,12 5,21 5,3"/>
              </svg>
              Reely
            </div>
            <p className="text-sm text-gray-500">
              © 2025 Reely. Enterprise video processing platform.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default SimpleLandingPage;