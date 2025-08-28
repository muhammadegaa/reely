import React from 'react';

// Professional loading component
export const LoadingSpinner = ({ 
  size = 'md',
  color = '#37353E'
}) => {
  const sizes = {
    sm: '16px',
    md: '24px',
    lg: '32px'
  };

  return (
    <div 
      className="loading-spinner" 
      style={{
        width: sizes[size],
        height: sizes[size],
        borderTopColor: color
      }}
    />
  );
};

// Professional loading component
export const Loader = ({ 
  message = "Processing...", 
  size = 'md',
  type = 'spinner' 
}) => {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '12px',
      justifyContent: 'center',
      flexDirection: 'column'
    }}>
      {type === 'dots' && (
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      )}
      
      {type === 'spinner' && (
        <LoadingSpinner size={size} />
      )}

      <span style={{
        fontSize: size === 'lg' ? '1rem' : size === 'sm' ? '0.75rem' : '0.875rem',
        color: 'var(--color-gray-600)',
        textAlign: 'center',
        fontWeight: '500'
      }}>
        {message}
      </span>
    </div>
  );
};

// Professional progress bar
export const ProgressBar = ({ 
  progress = 0, 
  showPercentage = true, 
  message = ""
}) => {
  return (
    <div style={{ width: '100%' }}>
      {message && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px'
        }}>
          <span style={{
            fontSize: '0.875rem',
            fontWeight: '500',
            color: 'var(--color-gray-700)'
          }}>
            {message}
          </span>
          {showPercentage && (
            <span style={{
              fontSize: '0.875rem',
              fontWeight: '600',
              color: 'var(--color-accent)'
            }}>
              {Math.round(progress)}%
            </span>
          )}
        </div>
      )}
      
      <div className="progress-bar">
        <div 
          className="progress-bar-fill"
          style={{
            width: `${Math.min(progress, 100)}%`,
            transition: 'width 0.3s ease-out'
          }}
        />
      </div>
    </div>
  );
};

// Professional button component
export const Button = ({
  children,
  onClick,
  loading = false,
  disabled = false,
  variant = 'primary',
  size = 'md',
  className = '',
  style = {},
  ...props
}) => {
  const baseClasses = `btn`;
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary'
  };
  const sizeClasses = {
    sm: '',
    md: 'btn-lg',
    lg: 'btn-xl'
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant] || variantClasses.primary} ${sizeClasses[size]} ${className}`}
      onClick={onClick}
      disabled={loading || disabled}
      style={style}
      {...props}
    >
      {loading ? (
        <>
          <LoadingSpinner size="sm" />
          Processing...
        </>
      ) : (
        children
      )}
    </button>
  );
};

// Static counter for stats
export const StatCounter = ({ 
  value, 
  suffix = '', 
  prefix = '', 
  className = '' 
}) => {
  return (
    <span className={className}>
      {prefix}{value}{suffix}
    </span>
  );
};

// Professional notification/toast
export const Toast = ({ 
  message, 
  type = 'success', 
  show = false, 
  onDismiss,
  duration = 4000 
}) => {
  React.useEffect(() => {
    if (show && duration > 0) {
      const timer = setTimeout(() => {
        onDismiss && onDismiss();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [show, duration, onDismiss]);

  if (!show) return null;

  const icons = {
    success: '✓',
    error: '⚠️',
    warning: '⚠️',
    info: 'i'
  };

  const colors = {
    success: { bg: '#f0fdf4', border: '#10b981', text: '#166534' },
    error: { bg: '#fef2f2', border: '#ef4444', text: '#dc2626' },
    warning: { bg: '#fffbeb', border: '#f59e0b', text: '#d97706' },
    info: { bg: '#eff6ff', border: '#3b82f6', text: '#2563eb' }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        background: colors[type].bg,
        border: `1px solid ${colors[type].border}`,
        borderRadius: '8px',
        padding: '12px 16px',
        color: colors[type].text,
        fontSize: '0.875rem',
        fontWeight: '500',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        zIndex: 10000,
        maxWidth: '400px',
        cursor: 'pointer'
      }}
      onClick={onDismiss}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span>{icons[type]}</span>
        {message}
        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', opacity: 0.7 }}>
          Click to dismiss
        </span>
      </div>
    </div>
  );
};

// Professional skeleton loader
export const SkeletonLoader = ({ 
  lines = 3, 
  width = '100%', 
  height = '1em',
  className = '' 
}) => {
  return (
    <div className={className}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="skeleton skeleton-text"
          style={{
            width: i === lines - 1 ? '80%' : width,
            height: height
          }}
        />
      ))}
    </div>
  );
};

