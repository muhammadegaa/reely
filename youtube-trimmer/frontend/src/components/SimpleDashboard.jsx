import React, { useState } from 'react';
import PremiumVideoProcessor from './PremiumVideoProcessor';

const SimpleDashboard = () => {
  const [activeTab, setActiveTab] = useState('create');

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

  const tabs = [
    { 
      id: 'create', 
      name: 'Create Video', 
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="5,3 19,12 5,21 5,3"/>
        </svg>
      )
    },
    { 
      id: 'about', 
      name: 'About', 
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4"/>
          <path d="M12 8h.01"/>
        </svg>
      )
    }
  ];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--color-gray-50)' }}>
      {/* Professional Header */}
      <header className="nav-header">
        <div className="nav-container">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <div className="nav-brand">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5,3 19,12 5,21 5,3"/>
              </svg>
              Reely
            </div>
            <div className="status-badge status-free">
              Demo Mode
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <div style={{ textAlign: 'right' }}>
              <p style={{ 
                margin: 0, 
                fontSize: 'var(--text-sm)', 
                fontWeight: 'var(--font-medium)',
                color: 'var(--color-gray-900)'
              }}>
                Demo User
              </p>
              <p style={{ 
                margin: 0, 
                fontSize: 'var(--text-xs)', 
                color: 'var(--color-gray-500)'
              }}>
                Trial Account
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard Content */}
      <div className="container" style={{ padding: 'var(--space-8) var(--space-6)' }}>
        {/* Dashboard Header */}
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <h1 className="text-3xl font-bold text-gray-900" style={{ 
            marginBottom: 'var(--space-2)',
            letterSpacing: '-0.02em'
          }}>
            Video Processing Platform
          </h1>
          <p className="text-gray-600">
            Transform YouTube content into optimized social media clips with automated processing
          </p>
        </div>

        {/* Modern Tab Navigation */}
        <div className="card" style={{ marginBottom: 'var(--space-8)' }}>
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--color-gray-200)',
            backgroundColor: 'var(--color-gray-50)',
            borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
            padding: '0 var(--space-4)'
          }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="btn btn-ghost"
                style={{
                  padding: 'var(--space-4) var(--space-4)',
                  borderRadius: 0,
                  border: 'none',
                  backgroundColor: activeTab === tab.id ? 'white' : 'transparent',
                  borderBottom: activeTab === tab.id ? '2px solid var(--color-accent)' : '2px solid transparent',
                  color: activeTab === tab.id ? 'var(--color-accent)' : 'var(--color-gray-600)',
                  fontWeight: activeTab === tab.id ? 'var(--font-semibold)' : 'var(--font-medium)',
                  gap: 'var(--space-2)',
                  transition: 'var(--transition-spring)',
                  position: 'relative',
                  top: '1px'
                }}
              >
                {tab.icon}
                {tab.name}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="card-body" style={{ padding: 'var(--space-8)' }}>
            {activeTab === 'create' && (
              <div>
                <PremiumVideoProcessor 
                  usage={null} 
                  subscription={null}
                  onUsageUpdate={() => {}}
                />
              </div>
            )}
            
            {activeTab === 'about' && (
              <div style={{ maxWidth: '800px' }}>
                <div style={{ marginBottom: 'var(--space-8)' }}>
                  <div className="feature-icon" style={{ 
                    marginBottom: 'var(--space-6)',
                    backgroundColor: 'var(--color-gray-100)',
                    border: '1px solid var(--color-gray-200)'
                  }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5,3 19,12 5,21 5,3"/>
                    </svg>
                  </div>
                  
                  <h2 className="text-2xl font-semibold text-gray-900" style={{ marginBottom: 'var(--space-4)' }}>
                    About Reely
                  </h2>
                  <p className="text-lg text-gray-600" style={{ 
                    marginBottom: 'var(--space-6)',
                    lineHeight: '1.6'
                  }}>
                    Enterprise video processing platform that transforms long-form YouTube content 
                    into optimized short-form videos for social media distribution using machine learning algorithms.
                  </p>
                </div>

                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
                  gap: 'var(--space-8)',
                  marginBottom: 'var(--space-8)'
                }}>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900" style={{ marginBottom: 'var(--space-4)' }}>
                      Key Features
                    </h3>
                    <ul style={{ 
                      margin: 0, 
                      padding: 0, 
                      listStyle: 'none',
                      color: 'var(--color-gray-600)',
                      lineHeight: '1.8'
                    }}>
                      <li style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12"/>
                        </svg>
                        AI-powered content analysis
                      </li>
                      <li style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12"/>
                        </svg>
                        Automated transcription services
                      </li>
                      <li style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12"/>
                        </svg>
                        Multi-format video optimization
                      </li>
                      <li style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12"/>
                        </svg>
                        Batch processing capabilities
                      </li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900" style={{ marginBottom: 'var(--space-4)' }}>
                      How It Works
                    </h3>
                    <ol style={{ 
                      margin: 0, 
                      padding: 0, 
                      listStyle: 'none',
                      color: 'var(--color-gray-600)',
                      lineHeight: '1.8'
                    }}>
                      <li style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                        <span style={{ 
                          backgroundColor: 'var(--color-accent)',
                          color: 'white',
                          borderRadius: '50%',
                          width: '20px',
                          height: '20px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 'var(--text-xs)',
                          fontWeight: 'var(--font-semibold)',
                          flexShrink: 0,
                          marginTop: '2px'
                        }}>
                          1
                        </span>
                        Input YouTube URL
                      </li>
                      <li style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                        <span style={{ 
                          backgroundColor: 'var(--color-accent)',
                          color: 'white',
                          borderRadius: '50%',
                          width: '20px',
                          height: '20px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 'var(--text-xs)',
                          fontWeight: 'var(--font-semibold)',
                          flexShrink: 0,
                          marginTop: '2px'
                        }}>
                          2
                        </span>
                        AI processes and analyzes content
                      </li>
                      <li style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                        <span style={{ 
                          backgroundColor: 'var(--color-accent)',
                          color: 'white',
                          borderRadius: '50%',
                          width: '20px',
                          height: '20px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 'var(--text-xs)',
                          fontWeight: 'var(--font-semibold)',
                          flexShrink: 0,
                          marginTop: '2px'
                        }}>
                          3
                        </span>
                        Review optimized segments
                      </li>
                      <li style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
                        <span style={{ 
                          backgroundColor: 'var(--color-accent)',
                          color: 'white',
                          borderRadius: '50%',
                          width: '20px',
                          height: '20px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 'var(--text-xs)',
                          fontWeight: 'var(--font-semibold)',
                          flexShrink: 0,
                          marginTop: '2px'
                        }}>
                          4
                        </span>
                        Export production-ready content
                      </li>
                    </ol>
                  </div>
                </div>

                {/* Call to Action in About */}
                <div style={{
                  backgroundColor: 'var(--color-gray-50)',
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-lg)',
                  padding: 'var(--space-6)',
                  textAlign: 'center'
                }}>
                  <p className="text-gray-700" style={{ marginBottom: 'var(--space-4)' }}>
                    Ready to start processing video content?
                  </p>
                  <button
                    onClick={() => setActiveTab('create')}
                    className="btn btn-primary btn-lg"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5,3 19,12 5,21 5,3"/>
                    </svg>
                    Start Processing
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleDashboard;