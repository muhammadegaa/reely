import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authAPI, healthAPI } from '../services/api';
import {
  Video,
  Scissors,
  Zap,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Crown,
  BarChart3,
  Play,
} from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();
  const [usage, setUsage] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [usageResponse, statsResponse] = await Promise.all([
        authAPI.getUsage(),
        healthAPI.check().catch(() => ({ data: null })) // Don't fail if stats endpoint fails
      ]);
      
      setUsage(usageResponse.data);
      if (statsResponse.data) {
        setStats(statsResponse.data);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSubscriptionStatus = () => {
    if (user?.subscription_tier === 'premium') {
      return {
        name: 'Premium',
        color: 'purple',
        icon: Crown,
        description: 'Unlimited everything + priority support',
      };
    }
    if (user?.subscription_tier === 'pro') {
      return {
        name: 'Pro',
        color: 'blue',
        icon: Zap,
        description: 'AI features + extended limits',
      };
    }
    return {
      name: 'Free',
      color: 'gray',
      icon: Video,
      description: 'Basic video trimming',
    };
  };

  const getUsagePercentage = (used, limit) => {
    if (limit === -1) return 0; // Unlimited
    return Math.min((used / limit) * 100, 100);
  };

  const subscription = getSubscriptionStatus();

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name || user?.email?.split('@')[0]}!
        </h1>
        <p className="mt-2 text-gray-600">
          Transform your YouTube videos into viral content with AI-powered trimming.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        <Link
          to="/trimmer"
          className="relative group bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg p-6 text-white hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Scissors className="h-8 w-8" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold">Trim Video</h3>
              <p className="text-blue-100">Start creating content</p>
            </div>
          </div>
          <div className="absolute top-4 right-4">
            <Play className="h-5 w-5 opacity-70" />
          </div>
        </Link>

        <Link
          to="/history"
          className="relative group bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-all duration-200"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="h-8 w-8 text-gray-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">View History</h3>
              <p className="text-gray-600">See past projects</p>
            </div>
          </div>
        </Link>

        <Link
          to="/subscription"
          className="relative group bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-all duration-200"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <subscription.icon className={`h-8 w-8 text-${subscription.color}-600`} />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {subscription.name} Plan
              </h3>
              <p className="text-gray-600">Manage subscription</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Usage Stats */}
      {usage && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Monthly Usage</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {/* Trims Usage */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <Scissors className="h-5 w-5 text-blue-600 mr-2" />
                  <h3 className="font-semibold text-gray-900">Video Trims</h3>
                </div>
                <span className="text-sm text-gray-500">
                  {usage.monthly_trims_used}/{usage.monthly_trims_limit === -1 ? '∞' : usage.monthly_trims_limit}
                </span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${getUsagePercentage(usage.monthly_trims_used, usage.monthly_trims_limit)}%` }}
                ></div>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">
                  {usage.monthly_trims_limit === -1 
                    ? 'Unlimited' 
                    : `${usage.monthly_trims_limit - usage.monthly_trims_used} remaining`}
                </span>
                <span className="text-gray-500">
                  Resets in {usage.days_until_reset} days
                </span>
              </div>
            </div>

            {/* Hooks Usage */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <Zap className="h-5 w-5 text-purple-600 mr-2" />
                  <h3 className="font-semibold text-gray-900">AI Hook Detection</h3>
                </div>
                <span className="text-sm text-gray-500">
                  {usage.monthly_hooks_used}/{usage.monthly_hooks_limit === -1 ? '∞' : usage.monthly_hooks_limit}
                </span>
              </div>
              
              {usage.monthly_hooks_limit === 0 ? (
                <div className="flex items-center text-sm text-gray-500">
                  <AlertCircle className="h-4 w-4 mr-2" />
                  Upgrade to Pro for AI features
                </div>
              ) : (
                <>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${getUsagePercentage(usage.monthly_hooks_used, usage.monthly_hooks_limit)}%` }}
                    ></div>
                  </div>
                  
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {usage.monthly_hooks_limit === -1 
                        ? 'Unlimited' 
                        : `${usage.monthly_hooks_limit - usage.monthly_hooks_used} remaining`}
                    </span>
                    <span className="text-gray-500">
                      Resets in {usage.days_until_reset} days
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Performance Stats */}
      {stats && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Your Performance</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-4">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900">{stats.user_stats.total_jobs}</h3>
              <p className="text-gray-600">Total Projects</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-4">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900">{stats.user_stats.completed_jobs}</h3>
              <p className="text-gray-600">Completed</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-4">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900">{stats.user_stats.success_rate}</h3>
              <p className="text-gray-600">Success Rate</p>
            </div>
          </div>
        </div>
      )}

      {/* Upgrade CTA for Free Users */}
      {user?.subscription_tier === 'free' && (
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2">Ready to unlock AI-powered features?</h3>
              <p className="text-blue-100">
                Upgrade to Pro for automatic hook detection, longer videos, and priority support.
              </p>
            </div>
            <div className="ml-6">
              <Link
                to="/subscription"
                className="bg-white text-blue-600 px-6 py-2 rounded-lg font-semibold hover:bg-gray-50 transition-colors duration-200"
              >
                Upgrade Now
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Getting Started Tips */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Getting Started</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="space-y-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center w-6 h-6 bg-blue-600 rounded-full">
                  <span className="text-xs font-semibold text-white">1</span>
                </div>
              </div>
              <div className="ml-3">
                <h4 className="font-semibold text-gray-900">Find a YouTube video</h4>
                <p className="text-gray-600">Copy the URL of any YouTube video you want to trim.</p>
              </div>
            </div>

            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center w-6 h-6 bg-blue-600 rounded-full">
                  <span className="text-xs font-semibold text-white">2</span>
                </div>
              </div>
              <div className="ml-3">
                <h4 className="font-semibold text-gray-900">Use AI or manual trimming</h4>
                <p className="text-gray-600">Let our AI find the best moments or set your own timestamps.</p>
              </div>
            </div>

            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center w-6 h-6 bg-blue-600 rounded-full">
                  <span className="text-xs font-semibold text-white">3</span>
                </div>
              </div>
              <div className="ml-3">
                <h4 className="font-semibold text-gray-900">Download and share</h4>
                <p className="text-gray-600">Get your trimmed video optimized for TikTok, Instagram, and more.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}