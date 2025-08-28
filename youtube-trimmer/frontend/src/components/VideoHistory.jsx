import React, { useState, useEffect } from 'react';
import { videoAPI } from '../services/api';

const VideoHistory = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    loadJobs();
  }, [page]);

  const loadJobs = async () => {
    try {
      const data = await videoAPI.getJobs(page, 10);
      if (page === 1) {
        setJobs(data.jobs || []);
      } else {
        setJobs(prev => [...prev, ...(data.jobs || [])]);
      }
      setHasMore(data.has_more || false);
    } catch (error) {
      setError('Failed to load video history');
      console.error('Error loading jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (downloadId) => {
    window.open(videoAPI.downloadVideo(downloadId), '_blank');
  };

  const handleDelete = async (jobId) => {
    if (!confirm('Are you sure you want to delete this video?')) return;

    try {
      await videoAPI.deleteJob(jobId);
      setJobs(jobs.filter(job => job.id !== jobId));
    } catch (error) {
      console.error('Failed to delete job:', error);
      alert('Failed to delete video. Please try again.');
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'processing': return '#f59e0b';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✅';
      case 'processing': return '⏳';
      case 'failed': return '❌';
      default: return '⏸️';
    }
  };

  if (loading && jobs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid #e5e7eb',
          borderTop: '4px solid #667eea',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          margin: '0 auto 16px'
        }} />
        <p style={{ color: '#6b7280' }}>Loading your videos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '40px',
        backgroundColor: '#fef2f2',
        border: '1px solid #fecaca',
        borderRadius: '8px'
      }}>
        <p style={{ color: '#dc2626', marginBottom: '16px' }}>{error}</p>
        <button
          onClick={() => {
            setError(null);
            setLoading(true);
            setPage(1);
            loadJobs();
          }}
          style={{
            padding: '8px 16px',
            backgroundColor: '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🎬</div>
        <h3 style={{ color: '#374151', marginBottom: '8px' }}>
          No videos yet
        </h3>
        <p style={{ color: '#6b7280', marginBottom: '24px' }}>
          Create your first video to see it appear here
        </p>
        <div style={{
          padding: '16px',
          backgroundColor: '#f0f9ff',
          border: '1px solid #bae6fd',
          borderRadius: '8px',
          maxWidth: '400px',
          margin: '0 auto'
        }}>
          <h4 style={{ color: '#1e40af', fontSize: '1rem', marginBottom: '8px' }}>
            💡 Pro Tip
          </h4>
          <p style={{ color: '#1e40af', fontSize: '0.875rem', margin: 0 }}>
            Use AI hook detection to automatically find the most engaging moments
            in your YouTube videos!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '8px'
        }}>
          Your Video History
        </h2>
        <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
          Manage and download your processed videos
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {jobs.map((job) => (
          <div
            key={job.id}
            style={{
              padding: '20px',
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              marginBottom: '12px'
            }}>
              <div style={{ flex: 1 }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '8px'
                }}>
                  <span>{getStatusIcon(job.status)}</span>
                  <span style={{
                    fontSize: '0.875rem',
                    fontWeight: '600',
                    color: getStatusColor(job.status),
                    textTransform: 'capitalize'
                  }}>
                    {job.status}
                  </span>
                  <span style={{
                    fontSize: '0.75rem',
                    color: '#6b7280'
                  }}>
                    • {formatDate(job.created_at)}
                  </span>
                </div>

                <h4 style={{
                  fontSize: '1rem',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '8px',
                  wordBreak: 'break-all'
                }}>
                  {job.input_url || 'Video Processing Job'}
                </h4>

                <div style={{
                  display: 'flex',
                  gap: '16px',
                  fontSize: '0.875rem',
                  color: '#6b7280'
                }}>
                  {job.start_time !== undefined && job.end_time !== undefined && (
                    <span>
                      Duration: {formatDuration(job.end_time - job.start_time)}
                    </span>
                  )}
                  {job.processing_options && (
                    <>
                      {job.processing_options.vertical_format && (
                        <span style={{ color: '#2563eb' }}>📱 Vertical</span>
                      )}
                      {job.processing_options.add_subtitles && (
                        <span style={{ color: '#7c3aed' }}>📝 Subtitles</span>
                      )}
                    </>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                {job.status === 'completed' && job.download_id && (
                  <button
                    onClick={() => handleDownload(job.download_id)}
                    style={{
                      padding: '8px 12px',
                      backgroundColor: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '0.875rem',
                      fontWeight: '500',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    ⬇️ Download
                  </button>
                )}
                <button
                  onClick={() => handleDelete(job.id)}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>

            {job.error_message && (
              <div style={{
                padding: '8px 12px',
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '6px',
                marginTop: '8px'
              }}>
                <p style={{
                  color: '#dc2626',
                  fontSize: '0.875rem',
                  margin: 0
                }}>
                  Error: {job.error_message}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <button
            onClick={() => {
              setPage(page + 1);
              setLoading(true);
            }}
            disabled={loading}
            style={{
              padding: '12px 24px',
              backgroundColor: loading ? '#9ca3af' : '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.875rem',
              fontWeight: '500',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Loading...' : 'Load More Videos'}
          </button>
        </div>
      )}

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default VideoHistory;