import React from 'react';

const UsageStats = ({ usage }) => {
  if (!usage) return null;

  const getProgressColor = (current, limit) => {
    if (limit === -1) return '#10b981'; // Unlimited - green
    const percentage = (current / limit) * 100;
    if (percentage >= 90) return '#ef4444'; // Red
    if (percentage >= 70) return '#f59e0b'; // Orange
    return '#10b981'; // Green
  };

  const getProgressWidth = (current, limit) => {
    if (limit === -1) return '100%';
    return `${Math.min((current / limit) * 100, 100)}%`;
  };

  const stats = [
    {
      label: 'Video Trims',
      current: usage.current_trims || 0,
      limit: usage.trims_limit,
      icon: '✂️'
    },
    {
      label: 'AI Hooks',
      current: usage.current_hooks || 0,
      limit: usage.hooks_limit,
      icon: '🤖'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px'
    }}>
      {stats.map((stat, index) => (
        <div key={index} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '1.5rem' }}>{stat.icon}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '4px'
            }}>
              <span style={{
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#374151'
              }}>
                {stat.label}
              </span>
              <span style={{
                fontSize: '0.875rem',
                fontWeight: '600',
                color: '#6b7280'
              }}>
                {stat.current} / {stat.limit === -1 ? '∞' : stat.limit}
              </span>
            </div>
            <div style={{
              width: '100%',
              height: '6px',
              backgroundColor: '#e5e7eb',
              borderRadius: '3px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: getProgressWidth(stat.current, stat.limit),
                height: '100%',
                backgroundColor: getProgressColor(stat.current, stat.limit),
                borderRadius: '3px',
                transition: 'width 0.3s ease'
              }} />
            </div>
            {stat.limit !== -1 && stat.current >= stat.limit && (
              <p style={{
                fontSize: '0.75rem',
                color: '#ef4444',
                marginTop: '4px',
                margin: 0
              }}>
                Limit reached - Upgrade to continue
              </p>
            )}
          </div>
        </div>
      ))}

      {/* Upgrade CTA if on free plan */}
      {usage.subscription_tier === 'free' && (
        <div style={{
          gridColumn: '1 / -1',
          padding: '12px 16px',
          backgroundColor: '#f0f9ff',
          border: '1px solid #bae6fd',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: '8px'
        }}>
          <div>
            <p style={{
              fontSize: '0.875rem',
              fontWeight: '500',
              color: '#1e40af',
              margin: 0
            }}>
              Need more? Upgrade for unlimited access
            </p>
            <p style={{
              fontSize: '0.75rem',
              color: '#6b7280',
              margin: 0
            }}>
              Pro: 100 trims, 50 hooks • Premium: Unlimited everything
            </p>
          </div>
          <button style={{
            padding: '6px 12px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.875rem',
            fontWeight: '500',
            cursor: 'pointer'
          }}>
            Upgrade
          </button>
        </div>
      )}
    </div>
  );
};

export default UsageStats;