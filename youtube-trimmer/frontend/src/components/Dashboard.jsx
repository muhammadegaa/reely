import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { authAPI, subscriptionAPI } from '../services/api';
import VideoProcessor from './VideoProcessor';
import VideoHistory from './VideoHistory';
import SubscriptionInfo from './SubscriptionInfo';
import UsageStats from './UsageStats';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('create');
  const [usage, setUsage] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [usageData, subscriptionData] = await Promise.all([
          authAPI.getUsage(),
          subscriptionAPI.getSubscription().catch(() => null)
        ]);
        setUsage(usageData);
        setSubscription(subscriptionData);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const tabs = [
    { id: 'create', name: 'Create Video', icon: '🎬' },
    { id: 'history', name: 'My Videos', icon: '📹' },
    { id: 'subscription', name: 'Subscription', icon: '💎' },
    { id: 'analytics', name: 'Analytics', icon: '📊' }
  ];

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #e5e7eb',
            borderTop: '4px solid #667eea',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }} />
          <p style={{ color: '#6b7280' }}>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc' }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        padding: '16px 24px'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <h1 style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              margin: 0
            }}>
              Reely
            </h1>
            <div style={{
              padding: '4px 12px',
              backgroundColor: getSubscriptionColor(user?.subscription_tier),
              borderRadius: '16px',
              fontSize: '0.75rem',
              fontWeight: '600',
              color: 'white',
              textTransform: 'uppercase'
            }}>
              {user?.subscription_tier || 'Free'}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ textAlign: 'right' }}>
              <p style={{ margin: 0, fontSize: '0.875rem', fontWeight: '500' }}>
                {user?.full_name || user?.email}
              </p>
              <p style={{ margin: 0, fontSize: '0.75rem', color: '#6b7280' }}>
                Member since {new Date(user?.created_at || Date.now()).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={logout}
              style={{
                padding: '8px 16px',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Usage Stats Bar */}
      {usage && (
        <div style={{
          backgroundColor: 'white',
          borderBottom: '1px solid #e5e7eb',
          padding: '12px 24px'
        }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
            <UsageStats usage={usage} />
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="container" style={{ padding: 'var(--space-6) var(--space-6)' }}>
        {/* Tab Navigation */}
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--color-gray-200)',
            backgroundColor: 'var(--color-gray-50)',
            borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0'
          }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`btn ${activeTab === tab.id ? 'btn-ghost' : 'btn-ghost'}`}
                style={{
                  flex: 1,
                  padding: 'var(--space-4)',
                  borderRadius: 0,
                  border: 'none',
                  backgroundColor: activeTab === tab.id ? 'white' : 'transparent',
                  borderBottom: activeTab === tab.id ? '2px solid var(--color-primary-600)' : '2px solid transparent',
                  color: activeTab === tab.id ? 'var(--color-primary-600)' : 'var(--color-gray-600)',
                  fontWeight: activeTab === tab.id ? 'var(--font-semibold)' : 'var(--font-medium)',
                  gap: 'var(--space-2)'
                }}
              >
                <span style={{ fontSize: 'var(--text-lg)' }}>{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="card-body">
            {activeTab === 'create' && (
              <VideoProcessor 
                usage={usage} 
                subscription={subscription}
                onUsageUpdate={setUsage}
              />
            )}
            {activeTab === 'history' && <VideoHistory />}
            {activeTab === 'subscription' && (
              <SubscriptionInfo 
                subscription={subscription} 
                onSubscriptionUpdate={setSubscription}
              />
            )}
            {activeTab === 'analytics' && (
              <div style={{ textAlign: 'center', padding: 'var(--space-16)' }}>
                <div className="feature-icon" style={{ 
                  color: 'var(--color-gray-400)', 
                  backgroundColor: 'var(--color-gray-100)',
                  marginBottom: 'var(--space-6)'
                }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M3 3v18h18"/>
                    <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-700" style={{ marginBottom: 'var(--space-4)' }}>
                  Analytics Dashboard
                </h3>
                <p className="text-gray-500">
                  Detailed analytics coming soon! Track your video performance,
                  engagement metrics, and content insights.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};

// Remove this function as we're now using CSS classes for status badges

export default Dashboard;