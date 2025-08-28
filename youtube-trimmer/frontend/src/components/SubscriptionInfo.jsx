import React, { useState } from 'react';
import { subscriptionAPI } from '../services/api';

const SubscriptionInfo = ({ subscription, onSubscriptionUpdate }) => {
  const [loading, setLoading] = useState(false);

  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      features: [
        '5 video trims per month',
        '3 AI hook detections',
        'Up to 5-minute videos',
        'TikTok/Instagram format',
        'Basic support'
      ],
      color: '#10b981',
      current: subscription?.tier === 'free' || !subscription
    },
    {
      name: 'Pro',
      price: '$19',
      period: 'per month',
      features: [
        '100 video trims per month',
        '50 AI hook detections',
        'Up to 30-minute videos',
        'All format options',
        'API access',
        'Priority support'
      ],
      color: '#f59e0b',
      current: subscription?.tier === 'pro',
      priceId: 'price_pro' // This should match your Stripe price ID
    },
    {
      name: 'Premium',
      price: '$49',
      period: 'per month',
      features: [
        'Unlimited video trims',
        'Unlimited AI hook detections',
        'Up to 2-hour videos',
        'All format options',
        'Full API access',
        'Priority processing',
        '24/7 premium support'
      ],
      color: '#8b5cf6',
      current: subscription?.tier === 'premium',
      priceId: 'price_premium' // This should match your Stripe price ID
    }
  ];

  const handleUpgrade = async (plan) => {
    if (plan.current || !plan.priceId) return;

    setLoading(true);
    try {
      const { checkout_url } = await subscriptionAPI.createCheckoutSession(plan.priceId);
      window.location.href = checkout_url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start checkout. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    if (!subscription) return;

    setLoading(true);
    try {
      const { portal_url } = await subscriptionAPI.createPortalSession();
      window.location.href = portal_url;
    } catch (error) {
      console.error('Failed to create portal session:', error);
      alert('Failed to open billing portal. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '8px'
        }}>
          Choose Your Plan
        </h2>
        <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
          Select the perfect plan for your content creation needs
        </p>
      </div>

      {/* Current Subscription Status */}
      {subscription && (
        <div style={{
          padding: '16px',
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          marginBottom: '24px'
        }}>
          <h3 style={{
            fontSize: '1.125rem',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '8px'
          }}>
            Current Subscription
          </h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{
                fontSize: '0.875rem',
                color: '#6b7280',
                margin: '4px 0'
              }}>
                Plan: <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>
                  {subscription.tier}
                </span>
              </p>
              {subscription.status && (
                <p style={{
                  fontSize: '0.875rem',
                  color: subscription.status === 'active' ? '#10b981' : '#ef4444',
                  margin: '4px 0',
                  fontWeight: '500'
                }}>
                  Status: {subscription.status}
                </p>
              )}
              {subscription.current_period_end && (
                <p style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                  margin: '4px 0'
                }}>
                  {subscription.cancel_at_period_end 
                    ? 'Ends on: ' 
                    : 'Renews on: '
                  }
                  {new Date(subscription.current_period_end).toLocaleDateString()}
                </p>
              )}
            </div>
            <button
              onClick={handleManageSubscription}
              disabled={loading}
              style={{
                padding: '8px 16px',
                backgroundColor: '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.875rem',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Loading...' : 'Manage Billing'}
            </button>
          </div>
        </div>
      )}

      {/* Plans Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '24px'
      }}>
        {plans.map((plan, index) => (
          <div
            key={index}
            style={{
              position: 'relative',
              padding: '24px',
              border: plan.current ? `2px solid ${plan.color}` : '1px solid #e5e7eb',
              borderRadius: '12px',
              backgroundColor: plan.current ? '#fafafa' : 'white',
              boxShadow: plan.current ? '0 8px 25px rgba(0,0,0,0.1)' : '0 4px 6px rgba(0,0,0,0.05)'
            }}
          >
            {plan.current && (
              <div style={{
                position: 'absolute',
                top: '-10px',
                left: '50%',
                transform: 'translateX(-50%)',
                padding: '4px 12px',
                backgroundColor: plan.color,
                color: 'white',
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: '600'
              }}>
                Current Plan
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <h3 style={{
                fontSize: '1.25rem',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '8px'
              }}>
                {plan.name}
              </h3>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{
                  fontSize: '2rem',
                  fontWeight: '700',
                  color: plan.color
                }}>
                  {plan.price}
                </span>
                <span style={{
                  fontSize: '0.875rem',
                  color: '#6b7280'
                }}>
                  {plan.period}
                </span>
              </div>
            </div>

            <ul style={{
              listStyle: 'none',
              padding: 0,
              margin: '0 0 24px 0'
            }}>
              {plan.features.map((feature, featureIndex) => (
                <li
                  key={featureIndex}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 0',
                    fontSize: '0.875rem',
                    color: '#374151'
                  }}
                >
                  <span style={{ color: plan.color, fontWeight: '600' }}>✓</span>
                  {feature}
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleUpgrade(plan)}
              disabled={loading || plan.current || !plan.priceId}
              style={{
                width: '100%',
                padding: '12px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.875rem',
                fontWeight: '600',
                cursor: (loading || plan.current || !plan.priceId) ? 'not-allowed' : 'pointer',
                backgroundColor: plan.current 
                  ? '#e5e7eb' 
                  : plan.priceId 
                    ? plan.color 
                    : '#f3f4f6',
                color: plan.current 
                  ? '#6b7280' 
                  : plan.priceId 
                    ? 'white' 
                    : '#6b7280',
                transition: 'all 0.2s'
              }}
              onMouseOver={(e) => {
                if (!plan.current && plan.priceId && !loading) {
                  e.target.style.opacity = '0.9';
                  e.target.style.transform = 'translateY(-2px)';
                }
              }}
              onMouseOut={(e) => {
                if (!plan.current && plan.priceId && !loading) {
                  e.target.style.opacity = '1';
                  e.target.style.transform = 'translateY(0)';
                }
              }}
            >
              {loading 
                ? 'Processing...' 
                : plan.current 
                  ? 'Current Plan' 
                  : plan.priceId 
                    ? `Upgrade to ${plan.name}` 
                    : 'Get Started'
              }
            </button>
          </div>
        ))}
      </div>

      {/* FAQ Section */}
      <div style={{ marginTop: '48px' }}>
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '24px',
          textAlign: 'center'
        }}>
          Frequently Asked Questions
        </h3>

        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          {[
            {
              question: 'Can I change plans anytime?',
              answer: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately with prorated billing.'
            },
            {
              question: 'What happens if I exceed my limits?',
              answer: 'On the free plan, you\'ll need to upgrade to continue. Pro and Premium plans have generous limits with overflow protection.'
            },
            {
              question: 'Do you offer refunds?',
              answer: 'We offer a 7-day satisfaction guarantee. If you\'re not happy, we\'ll provide a full refund, no questions asked.'
            },
            {
              question: 'Is there an API available?',
              answer: 'Yes! Pro and Premium plans include API access so you can integrate Reely into your own applications.'
            }
          ].map((faq, index) => (
            <div
              key={index}
              style={{
                marginBottom: '16px',
                padding: '16px',
                border: '1px solid #e5e7eb',
                borderRadius: '8px'
              }}
            >
              <h4 style={{
                fontSize: '1rem',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '8px'
              }}>
                {faq.question}
              </h4>
              <p style={{
                fontSize: '0.875rem',
                color: '#6b7280',
                margin: 0,
                lineHeight: 1.5
              }}>
                {faq.answer}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SubscriptionInfo;