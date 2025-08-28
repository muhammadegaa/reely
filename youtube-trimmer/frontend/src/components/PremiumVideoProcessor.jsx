import React, { useState } from 'react';
import { jobTracker, useJobTracker } from '../services/jobTracker';
import PremiumTimeline from './PremiumTimeline';
import '../styles/reely-colors.css';

const PremiumVideoProcessor = ({ usage, subscription, onUsageUpdate }) => {
  const [formData, setFormData] = useState({
    url: '',
    verticalFormat: false,
    addSubtitles: false
  });
  
  // Timeline state
  const [videoDuration, setVideoDuration] = useState(300);
  const [startTime, setStartTime] = useState(30);
  const [endTime, setEndTime] = useState(60);
  
  // Job tracking states
  const [trimJobId, setTrimJobId] = useState(null);
  const [hooksJobId, setHooksJobId] = useState(null);
  const [hooks, setHooks] = useState(null);
  const [error, setError] = useState(null);
  const [aiProvider, setAiProvider] = useState('openai');
  
  // Video preview state
  const [showPreview, setShowPreview] = useState(false);
  const [previewSettings, setPreviewSettings] = useState({
    volume: 1,
    playbackSpeed: 1,
    filters: {
      brightness: 100,
      contrast: 100,
      saturation: 100
    }
  });
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  // Use job tracker hooks
  const trimJob = useJobTracker(trimJobId);
  const hooksJob = useJobTracker(hooksJobId);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Show preview section when URL is entered
    if (name === 'url' && value.trim()) {
      setShowPreview(true);
      setError(null);
      // Preview section will show immediately, user can click "Quick Preview" to generate
    }
  };

  const validateForm = () => {
    if (!formData.url) {
      setError('Please enter a YouTube URL');
      return false;
    }
    if (startTime >= endTime) {
      setError('Start time must be less than end time');
      return false;
    }
    return true;
  };

  const handleTimelineChange = (newStart, newEnd) => {
    setStartTime(newStart);
    setEndTime(newEnd);
  };

  const handleTimelineHookSelect = (hook) => {
    setStartTime(hook.start);
    setEndTime(hook.end);
    setShowPreview(true);
    setError(null);
    
    // Generate preview for the selected hook
    setTimeout(() => generateVideoPreview(), 500);
    
    // Scroll to preview section
    setTimeout(() => {
      const previewElement = document.querySelector('[data-preview="true"]');
      if (previewElement) {
        previewElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
  };
  
  const handlePreviewSettingsChange = (setting, value) => {
    setPreviewSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };
  
  // Debounce filter changes to avoid too many API calls
  const [filterUpdateTimer, setFilterUpdateTimer] = useState(null);
  
  const handleFilterChange = (filter, value) => {
    setPreviewSettings(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [filter]: value
      }
    }));
    
    // Clear existing timer
    if (filterUpdateTimer) {
      clearTimeout(filterUpdateTimer);
    }
    
    // Set new timer for debounced preview update
    const newTimer = setTimeout(() => {
      if (previewData && showPreview && !previewLoading) {
        generateVideoPreview();
      }
    }, 500); // Wait 500ms after user stops adjusting
    
    setFilterUpdateTimer(newTimer);
  };
  
  const generateVideoPreview = async () => {
    if (!formData.url || startTime >= endTime) {
      setPreviewError('Invalid video URL or timing');
      return;
    }
    
    setPreviewLoading(true);
    setPreviewError(null);
    
    try {
      const formDataPreview = new FormData();
      formDataPreview.append('url', formData.url);
      formDataPreview.append('start_time', startTime);
      formDataPreview.append('end_time', endTime);
      formDataPreview.append('brightness', previewSettings.filters.brightness);
      formDataPreview.append('contrast', previewSettings.filters.contrast);
      formDataPreview.append('saturation', previewSettings.filters.saturation);
      
      const response = await fetch('http://localhost:8000/preview', {
        method: 'POST',
        body: formDataPreview
      });
      
      if (!response.ok) {
        throw new Error(`Preview generation failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      setPreviewData(result);
      
    } catch (err) {
      console.error('Preview generation error:', err);
      setPreviewError(err.message || 'Failed to generate preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const formatSecondsToTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    if (!validateForm()) return;

    try {
      const asyncFormData = new FormData();
      asyncFormData.append('url', formData.url);
      asyncFormData.append('start_time', formatSecondsToTime(startTime));
      asyncFormData.append('end_time', formatSecondsToTime(endTime));
      asyncFormData.append('vertical_format', formData.verticalFormat);
      asyncFormData.append('add_subtitles', formData.addSubtitles);

      const jobData = await jobTracker.startTrimJob(asyncFormData);
      setTrimJobId(jobData.job_id);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_trims: usage.current_trims + 1
        });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to start video processing. Please try again.';
      setError(errorMsg);
    }
  };

  const handleAutoHooks = async () => {
    setError(null);
    setHooks(null);
    
    if (!formData.url) {
      setError('Please enter a YouTube URL first');
      return;
    }

    try {
      const jobData = await jobTracker.startHooksJob(formData.url, aiProvider);
      setHooksJobId(jobData.job_id);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_hooks: usage.current_hooks + 1
        });
      }
    } catch (err) {
      let errorMessage = 'Failed to start AI analysis. Please try again.';
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      setError(errorMessage);
    }
  };

  // Handle hooks job completion
  React.useEffect(() => {
    if (hooksJob?.jobStatus?.status === 'completed' && hooksJob.jobStatus.result) {
      setHooks(hooksJob.jobStatus.result);
      
      // Update video duration if available from hook detection
      if (hooksJob.jobStatus.result.video_duration) {
        setVideoDuration(hooksJob.jobStatus.result.video_duration);
      }
      
      // Auto-show preview when hooks are found
      setShowPreview(true);
      
      // Generate initial preview with default timeline selection
      if (formData.url && startTime < endTime) {
        setTimeout(() => {
          generateVideoPreview();
        }, 1000);
      }
      
      setHooksJobId(null);
    } else if (hooksJob?.jobStatus?.status === 'failed') {
      setError(hooksJob.jobStatus.error || 'Hook analysis failed');
      setHooksJobId(null);
    }
  }, [hooksJob?.jobStatus]);

  const handleDownload = () => {
    if (trimJob?.downloadUrl) {
      window.open(trimJob.downloadUrl, '_blank');
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const ProgressIndicator = ({ job, type }) => {
    if (!job?.jobStatus) return null;

    const { status, progress, message, estimatedTimeRemaining } = job.jobStatus;
    
    return (
      <div className="status-processing" style={{
        marginTop: 'var(--space-8)',
        padding: 'clamp(1.5rem, 3vw, 2.5rem)',
        borderRadius: 'var(--radius-xl)',
        background: 'linear-gradient(135deg, var(--primary-subtle) 0%, var(--surface) 100%)'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start',
          marginBottom: 'var(--space-6)' 
        }}>
          <div>
            <h3 style={{ 
              margin: 0, 
              color: 'var(--text-primary)', 
              fontSize: 'var(--font-size-xl)', 
              fontWeight: 'var(--font-weight-bold)',
              letterSpacing: '-0.02em',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)'
            }}>
              {type === 'trim' ? (
                <>
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ color: 'var(--primary)' }}>
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                  </svg>
                  Processing Video
                </>
              ) : (
                <>
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ color: 'var(--primary)' }}>
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  AI Analysis
                </>
              )}
            </h3>
            <p style={{ 
              margin: 'var(--space-1) 0 0 0', 
              color: 'var(--text-secondary)', 
              fontSize: 'var(--font-size-base)',
              lineHeight: '1.5'
            }}>
              {message}
            </p>
          </div>
          
          <div style={{
            backgroundColor: 'var(--primary)',
            color: 'var(--text-on-mint)',
            padding: '8px 16px',
            borderRadius: 'var(--radius-xl)',
            fontWeight: 'var(--font-weight-bold)',
            fontSize: 'var(--font-size-sm)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            {progress}%
          </div>
        </div>

        {/* Progress bar */}
        <div style={{
          width: '100%',
          height: '12px',
          backgroundColor: 'var(--border)',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          marginBottom: estimatedTimeRemaining ? 'var(--space-4)' : '0',
          border: '1px solid var(--border-strong)'
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            background: 'linear-gradient(90deg, var(--primary) 0%, var(--primary-hover) 100%)',
            borderRadius: 'var(--radius-md)',
            transition: 'width 0.4s ease',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%)',
              animation: progress < 100 ? 'shimmer 2s infinite' : 'none'
            }} />
          </div>
        </div>

        {estimatedTimeRemaining && (
          <p style={{ 
            margin: 0, 
            color: 'var(--text-secondary)', 
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-medium)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)'
          }}>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
            About {job.formatTime(estimatedTimeRemaining)} remaining
          </p>
        )}
      </div>
    );
  };

  return (
    <div style={{ 
      maxWidth: '1200px', 
      margin: '0 auto', 
      padding: 'var(--space-10) var(--space-5)',
      backgroundColor: 'var(--background)',
      minHeight: '100vh',
      fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header - Professional & Clean */}
      <header style={{ 
        marginBottom: 'var(--space-12)', 
        textAlign: 'center',
        paddingBottom: 'var(--space-8)'
      }}>
        <div style={{
          marginBottom: 'var(--space-6)'
        }}>
          <h1 style={{ 
            color: 'var(--text-primary)', 
            margin: 0, 
            fontSize: 'var(--font-size-4xl)',
            fontWeight: 'var(--font-weight-bold)',
            letterSpacing: '-0.02em',
            lineHeight: '1.2'
          }}>
            Reely
          </h1>
        </div>
        <p style={{ 
          color: 'var(--text-secondary)', 
          fontSize: 'var(--font-size-lg)', 
          fontWeight: 'var(--font-weight-normal)',
          maxWidth: '500px',
          margin: 'var(--space-4) auto 0',
          lineHeight: '1.5'
        }}>
          AI-powered video trimming and editing
        </p>
      </header>

      <main className="card" style={{ 
        padding: 'var(--space-10)',
        marginBottom: 'var(--space-12)'
      }}>
        <form onSubmit={handleSubmit}>
          {/* YouTube URL Input */}
          <section style={{ marginBottom: 'var(--space-12)' }}>
            <div style={{ marginBottom: 'var(--space-6)' }}>
              <h2 style={{
                fontSize: 'var(--font-size-2xl)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--text-primary)',
                margin: '0 0 var(--space-2) 0'
              }}>
                Video Source
              </h2>
              <p style={{
                color: 'var(--text-secondary)',
                fontSize: 'var(--font-size-sm)',
                margin: 0,
                fontWeight: 'var(--font-weight-normal)'
              }}>
                Enter a YouTube URL to begin video analysis and editing
              </p>
            </div>
            
            <div style={{ position: 'relative' }}>
              <input
                type="url"
                name="url"
                value={formData.url}
                onChange={handleInputChange}
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                style={{
                  width: '100%',
                  padding: 'var(--space-5) var(--space-6)',
                  border: `2px solid var(--border)`,
                  borderRadius: 'var(--radius-lg)',
                  fontSize: 'var(--font-size-base)',
                  backgroundColor: 'var(--background)',
                  transition: 'all 0.2s ease',
                  fontFamily: 'inherit',
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--primary)';
                  e.target.style.boxShadow = `0 0 0 3px var(--mint)`;
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--border)';
                  e.target.style.boxShadow = 'none';
                }}
                required
              />
              {formData.url && (
                <div style={{
                  position: 'absolute',
                  right: 'var(--space-4)',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--success)'
                }} />
              )}
            </div>
            
            {/* Quick Preview Button */}
            {formData.url && (
              <div style={{ marginTop: 'var(--space-6)' }}>
                <button
                  type="button"
                  className="button-primary"
                  onClick={() => {
                    setShowPreview(true);
                    generateVideoPreview();
                  }}
                  disabled={previewLoading}
                  style={{
                    padding: 'var(--space-4) var(--space-8)',
                    fontSize: 'var(--font-size-sm)',
                    cursor: previewLoading ? 'not-allowed' : 'pointer',
                    opacity: previewLoading ? 0.6 : 1,
                    width: 'auto',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)'
                  }}
                >
                  {previewLoading ? (
                    <>
                      <div style={{
                        width: '16px',
                        height: '16px',
                        border: '2px solid var(--text-on-mint)',
                        borderTop: '2px solid transparent',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                      }} />
                      Generating Preview
                    </>
                  ) : (
                    'Generate Preview'
                  )}
                </button>
                <p style={{
                  margin: 'var(--space-2) 0 0 0',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-muted)',
                  fontWeight: 'var(--font-weight-normal)'
                }}>
                  Preview current timeline selection (30s-60s)
                </p>
              </div>
            )}
          </section>

          {/* AI Hook Detection */}
          <section className="surface" style={{
            marginBottom: 'var(--space-12)',
            padding: 'var(--space-10)',
            border: `1px solid var(--border)`
          }}>
            <div style={{ marginBottom: 'var(--space-8)' }}>
              <h2 style={{
                fontSize: 'var(--font-size-2xl)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--text-primary)',
                margin: '0 0 var(--space-2) 0'
              }}>
                AI Analysis
              </h2>
              <p style={{
                color: 'var(--text-secondary)',
                fontSize: 'var(--font-size-sm)',
                margin: 0,
                fontWeight: 'var(--font-weight-normal)'
              }}>
                Let AI identify the most engaging moments in your video
              </p>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', flexDirection: 'column', minWidth: '200px' }}>
                <label style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--text-secondary)',
                  marginBottom: 'var(--space-2)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  AI Provider
                </label>
                <select
                  value={aiProvider}
                  onChange={(e) => setAiProvider(e.target.value)}
                  style={{
                    padding: 'var(--space-3) var(--space-4)',
                    border: `2px solid var(--border)`,
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--background)',
                    fontSize: 'var(--font-size-sm)',
                    fontFamily: 'inherit',
                    color: 'var(--text-primary)',
                    fontWeight: 'var(--font-weight-medium)',
                    cursor: 'pointer'
                  }}
                >
                  <option value="openai">OpenAI GPT-4</option>
                  <option value="anthropic">Anthropic Claude</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ height: 'var(--space-5)' }} />
                <button
                  type="button"
                  className={hooksJobId || !formData.url ? 'button-secondary' : 'button-primary'}
                  onClick={handleAutoHooks}
                  disabled={!!hooksJobId || !formData.url}
                  style={{
                    padding: 'var(--space-4) var(--space-8)',
                    fontSize: 'var(--font-size-sm)',
                    cursor: (hooksJobId || !formData.url) ? 'not-allowed' : 'pointer',
                    opacity: (hooksJobId || !formData.url) ? 0.6 : 1,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)'
                  }}
                >
                  {hooksJobId ? (
                    <>
                      <div style={{
                        width: '16px',
                        height: '16px',
                        border: hooksJobId && formData.url ? '2px solid var(--text-on-mint)' : '2px solid var(--text-primary)',
                        borderTop: hooksJobId && formData.url ? '2px solid transparent' : '2px solid var(--primary)',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                      }} />
                      Analyzing Video
                    </>
                  ) : (
                    'Find Hook Points'
                  )}
                </button>
              </div>
            </div>
            
            {usage && (
              <div style={{
                marginTop: 'var(--space-6)',
                padding: 'var(--space-4)',
                backgroundColor: 'var(--background)',
                border: `1px solid var(--border)`,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-secondary)',
                  fontWeight: 'var(--font-weight-medium)'
                }}>
                  Usage this month
                </span>
                <span style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--text-primary)',
                  fontWeight: 'var(--font-weight-semibold)'
                }}>
                  {usage.current_hooks} / {usage.hooks_limit === -1 ? '∞' : usage.hooks_limit}
                </span>
              </div>
            )}
          </section>

          {/* Show hooks job progress */}
          {hooksJobId && <ProgressIndicator job={hooksJob} type="hooks" />}

          {/* Hook Selection Results */}
          {hooks && hooks.hooks && hooks.hooks.length > 0 && (
            <section className="card" style={{
              marginBottom: 'var(--space-12)',
              padding: 'var(--space-10)'
            }}>
              <div style={{ marginBottom: 'var(--space-8)' }}>
                <h2 style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  color: 'var(--text-primary)',
                  margin: '0 0 var(--space-2) 0'
                }}>
                  Hook Points Found
                </h2>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-4)'
                }}>
                  <span style={{
                    color: 'var(--text-secondary)',
                    fontSize: 'var(--font-size-sm)'
                  }}>
                    {hooks.hooks.length} engaging moments identified
                  </span>
                  <div style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--primary-light)',
                    color: 'var(--primary)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 'var(--font-weight-medium)',
                    border: '1px solid var(--primary)'
                  }}>
                    AI Analyzed
                  </div>
                </div>
              </div>
              
              <div style={{ display: 'grid', gap: '20px' }}>
                {hooks.hooks.map((hook, index) => {
                  const videoId = formData.url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
                  const embedUrl = videoId ? `https://www.youtube.com/embed/${videoId[1]}?start=${Math.floor(hook.start)}&end=${Math.floor(hook.end)}&autoplay=0&controls=1` : null;
                  
                  return (
                    <div key={index} style={{
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-lg)',
                      overflow: 'hidden',
                      transition: 'border-color 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border-strong)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border)';
                    }}>
                      <div style={{ display: 'grid', gridTemplateColumns: embedUrl ? '1fr 300px' : '1fr', gap: 0 }}>
                        {/* Hook Details */}
                        <div style={{ padding: 'var(--space-6)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                            <div>
                              <h4 style={{ 
                                margin: '0 0 var(--space-2) 0', 
                                fontSize: 'var(--font-size-lg)', 
                                fontWeight: 'var(--font-weight-semibold)',
                                color: 'var(--text-primary)',
                                letterSpacing: 0
                              }}>
                                {hook.title || `Hook Point ${index + 1}`}
                              </h4>
                              
                              <div style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '12px',
                                marginBottom: '12px'
                              }}>
                                <span style={{ 
                                  backgroundColor: 'var(--primary-light)',
                                  color: 'var(--primary)',
                                  padding: '4px 10px',
                                  borderRadius: 'var(--radius-md)',
                                  fontSize: 'var(--font-size-xs)',
                                  fontWeight: 'var(--font-weight-medium)',
                                  border: '1px solid var(--primary)'
                                }}>
                                  {formatSecondsToTime(hook.start)} - {formatSecondsToTime(hook.end)}
                                </span>
                                
                                <span style={{ 
                                  backgroundColor: 'var(--surface)',
                                  color: 'var(--text-secondary)',
                                  padding: '4px 10px',
                                  borderRadius: 'var(--radius-md)',
                                  fontSize: 'var(--font-size-xs)',
                                  fontWeight: 'var(--font-weight-medium)',
                                  border: '1px solid var(--border)'
                                }}>
                                  {formatTime(hook.end - hook.start)} duration
                                </span>
                              </div>
                            </div>
                          </div>
                          
                          {hook.reason && (
                            <p style={{ 
                              fontSize: 'var(--font-size-sm)', 
                              color: 'var(--text-secondary)', 
                              lineHeight: '1.5',
                              margin: '0 0 var(--space-5) 0'
                            }}>
                              {hook.reason}
                            </p>
                          )}
                          
                          <button
                            onClick={() => handleTimelineHookSelect(hook)}
                            className="button-primary"
                            style={{
                              fontSize: 'var(--font-size-sm)'
                            }}
                          >
                            Use This Hook
                          </button>
                        </div>
                        
                        {/* Video Preview */}
                        {embedUrl && (
                          <div style={{ 
                            backgroundColor: 'var(--surface)',
                            padding: 'var(--space-4)',
                            display: 'flex',
                            flexDirection: 'column',
                            borderLeft: '1px solid var(--border)'
                          }}>
                            <div style={{ 
                              fontSize: 'var(--font-size-xs)', 
                              color: 'var(--text-secondary)', 
                              fontWeight: 'var(--font-weight-medium)',
                              marginBottom: 'var(--space-3)',
                              textAlign: 'center'
                            }}>
                              Preview
                            </div>
                            
                            <div style={{
                              aspectRatio: '16/9',
                              borderRadius: 'var(--radius-md)',
                              overflow: 'hidden',
                              backgroundColor: 'var(--surface)',
                              border: '1px solid var(--border)'
                            }}>
                              <div
                                onClick={() => handleTimelineHookSelect(hook)}
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  backgroundColor: 'var(--surface)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  cursor: 'pointer',
                                  color: 'var(--text-secondary)',
                                  fontSize: 'var(--font-size-sm)',
                                  fontWeight: 'var(--font-weight-medium)',
                                  transition: 'background-color 0.15s ease',
                                  border: 'none'
                                }}
                                onMouseEnter={(e) => {
                                  e.target.style.backgroundColor = 'var(--primary-light)';
                                  e.target.style.color = 'var(--primary)';
                                }}
                                onMouseLeave={(e) => {
                                  e.target.style.backgroundColor = 'var(--surface)';
                                  e.target.style.color = 'var(--text-secondary)';
                                }}
                              >
                                Preview Hook
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              
              <div style={{
                marginTop: 'var(--space-6)',
                padding: 'var(--space-4)',
                backgroundColor: 'var(--primary-light)',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                border: '1px solid var(--primary)'
              }}>
                <p style={{ 
                  fontSize: 'var(--font-size-sm)', 
                  color: 'var(--primary)', 
                  margin: 0,
                  fontWeight: 'var(--font-weight-medium)'
                }}>
                  Click "Use This Hook" to automatically set your trim points, or manually adjust the timeline below
                </p>
              </div>
            </section>
          )}

          {/* Video Preview & Editor */}
          {(showPreview || formData.url.trim()) && (
            <div data-preview="true" className="card" style={{
              marginBottom: 'var(--space-10)',
              padding: '0',
              overflow: 'hidden'
            }}>
              {/* Preview Header */}
              <div style={{
                padding: 'var(--space-6) var(--space-8) var(--space-4) var(--space-8)',
                borderBottom: '1px solid var(--border)',
                backgroundColor: 'var(--surface)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ 
                    margin: 0, 
                    color: 'var(--text-primary)', 
                    fontSize: 'var(--font-size-xl)',
                    fontWeight: 'var(--font-weight-semibold)',
                    letterSpacing: 0,
                    fontFamily: 'inherit'
                  }}>
                    Video Preview
                  </h3>
                  
                  <button
                    onClick={() => setShowPreview(false)}
                    className="button-secondary"
                    style={{
                      fontSize: 'var(--font-size-sm)',
                      padding: 'var(--space-2) var(--space-4)'
                    }}
                  >
                    Close
                  </button>
                </div>
                
                <p style={{ 
                  margin: 'var(--space-2) 0 0 0', 
                  color: 'var(--text-secondary)', 
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-normal)'
                }}>
                  Preview and adjust your clip before exporting
                </p>
              </div>

              <div className="preview-grid" style={{ 
                display: 'grid', 
                gridTemplateColumns: window.innerWidth > 768 ? '1fr 320px' : '1fr',
                gap: '0'
              }}>
                {/* Video Player */}
                <div style={{ padding: 'var(--space-8)' }}>
                  <div style={{
                    aspectRatio: formData.verticalFormat ? '9/16' : '16/9',
                    maxWidth: formData.verticalFormat ? '300px' : '100%',
                    margin: '0 auto',
                    backgroundColor: 'var(--surface)',
                    borderRadius: 'var(--radius-lg)',
                    overflow: 'hidden',
                    border: '1px solid var(--border)'
                  }}>
                    {previewLoading ? (
                      <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-secondary)',
                        fontSize: 'var(--font-size-base)',
                        gap: 'var(--space-4)'
                      }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          border: '3px solid var(--border)',
                          borderTop: '3px solid var(--primary)',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite'
                        }}></div>
                        <div>Generating preview...</div>
                      </div>
                    ) : previewError ? (
                      <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-primary)',
                        fontSize: 'var(--font-size-base)',
                        padding: 'var(--space-5)',
                        textAlign: 'center',
                        gap: 'var(--space-4)'
                      }}>
                        <div>Preview Error</div>
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>{previewError}</div>
                        <button
                          onClick={generateVideoPreview}
                          className="button-primary"
                          style={{
                            fontSize: 'var(--font-size-sm)',
                            padding: 'var(--space-2) var(--space-4)'
                          }}
                        >
                          Try Again
                        </button>
                      </div>
                    ) : previewData ? (
                      <video
                        key={previewData.preview_id}
                        controls
                        style={{
                          width: '100%',
                          height: '100%',
                          backgroundColor: 'var(--surface)'
                        }}
                        volume={previewSettings.volume}
                        playbackRate={previewSettings.playbackSpeed}
                      >
                        <source src={`http://localhost:8000/preview/${previewData.preview_id}`} type="video/mp4" />
                        Your browser does not support the video tag.
                      </video>
                    ) : (
                      <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-secondary)',
                        fontSize: 'var(--font-size-base)',
                        gap: 'var(--space-4)'
                      }}>
                        <div>Video Preview</div>
                        <button
                          onClick={generateVideoPreview}
                          className="button-primary"
                        >
                          Generate Preview
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {/* Video Info */}
                  <div style={{
                    marginTop: 'var(--space-6)',
                    padding: 'var(--space-5)',
                    backgroundColor: 'var(--surface)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border)'
                  }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                      gap: 'var(--space-4)',
                      textAlign: 'center'
                    }}>
                      <div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)' }}>START</div>
                        <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>{formatSecondsToTime(startTime)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)' }}>END</div>
                        <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>{formatSecondsToTime(endTime)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)' }}>DURATION</div>
                        <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--primary)' }}>{formatTime(endTime - startTime)}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Edit Controls */}
                <div className="preview-controls" style={{
                  padding: 'var(--space-8)',
                  backgroundColor: 'var(--surface)',
                  borderLeft: window.innerWidth > 768 ? '1px solid var(--border)' : 'none',
                  borderTop: window.innerWidth <= 768 ? '1px solid var(--border)' : 'none'
                }}>
                  <h4 style={{
                    margin: '0 0 var(--space-5) 0',
                    fontSize: 'var(--font-size-base)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--text-primary)',
                    letterSpacing: 0
                  }}>
                    Quick Adjustments
                  </h4>
                  
                  {/* Visual Filters */}
                  <div style={{ marginBottom: 'var(--space-6)' }}>
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      fontSize: '13px', 
                      fontWeight: '600', 
                      color: 'var(--text-secondary)', 
                      marginBottom: '12px' 
                    }}>
                      <span>Visual Filters</span>
                      {filterUpdateTimer && (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '11px',
                          color: 'var(--primary)',
                          fontWeight: '600'
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--primary)',
                            animation: 'pulse 1s infinite'
                          }}></div>
                          Updating...
                        </div>
                      )}
                    </div>
                    
                    {Object.entries(previewSettings.filters).map(([filter, value]) => (
                      <div key={filter} style={{ marginBottom: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: '500', textTransform: 'capitalize' }}>
                            {filter}
                          </span>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600' }}>
                            {value}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="50"
                          max="150"
                          value={value}
                          onChange={(e) => handleFilterChange(filter, parseInt(e.target.value))}
                          style={{
                            width: '100%',
                            height: '6px',
                            borderRadius: '3px',
                            background: `linear-gradient(to right, var(--primary) 0%, var(--primary) ${(value-50)/100*100}%, var(--surface) ${(value-50)/100*100}%, var(--surface) 100%)`,
                            outline: 'none',
                            border: '1px solid var(--primary)',
                            cursor: 'pointer'
                          }}
                        />
                      </div>
                    ))}
                  </div>
                  
                  {/* Format Preview */}
                  <div style={{
                    padding: '16px',
                    backgroundColor: 'var(--surface)',
                    borderRadius: '8px',
                    border: '1px solid var(--primary)',
                    marginBottom: '20px'
                  }}>
                    <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '8px' }}>Export Format</div>
                    <div style={{ fontSize: '14px', color: 'var(--text-primary)', fontWeight: '600' }}>
                      {formData.verticalFormat ? '📱 Vertical (9:16)' : '🖥️ Horizontal (16:9)'}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {formData.addSubtitles ? '✓ With Subtitles' : '○ No Subtitles'}
                    </div>
                  </div>
                  
                  {/* Real-time Preview Controls */}
                  <div style={{  
                    padding: '16px',
                    backgroundColor: 'var(--surface)',
                    borderRadius: '8px',
                    border: '1px solid var(--primary)',
                    marginBottom: '20px'
                  }}>
                    <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '12px' }}>Preview Controls</div>
                    
                    <button
                      onClick={() => {
                        if (previewData) {
                          generateVideoPreview();
                        }
                      }}
                      disabled={previewLoading || !formData.url}
                      style={{
                        width: '100%',
                        padding: '10px',
                        backgroundColor: previewLoading ? 'var(--surface)' : 'var(--primary)',
                        color: previewLoading ? 'var(--text-muted)' : 'var(--text-primary)',
                        border: '1px solid var(--primary)',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: '600',
                        cursor: previewLoading || !formData.url ? 'not-allowed' : 'pointer',
                        marginBottom: '8px',
                        fontFamily: 'Inter, system-ui, sans-serif'
                      }}
                    >
                      {previewLoading ? '⏳ Updating...' : '🔄 Update Preview'}
                    </button>
                  </div>
                  
                  {/* Reset Button */}
                  <button
                    onClick={() => {
                      setPreviewSettings({
                        volume: 1,
                        playbackSpeed: 1,
                        filters: { brightness: 100, contrast: 100, saturation: 100 }
                      });
                      // Regenerate preview with reset values
                      if (previewData && showPreview) {
                        setTimeout(() => generateVideoPreview(), 100);
                      }
                    }}
                    style={{
                      width: '100%',
                      padding: '12px',
                      backgroundColor: 'transparent',
                      color: 'var(--text-muted)',
                      border: '1px solid var(--primary)',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      fontFamily: 'Inter, system-ui, sans-serif'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = 'var(--primary)';
                      e.target.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = 'transparent';
                      e.target.style.color = 'var(--text-muted)';
                    }}
                  >
                    ↻ Reset All
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Video Timeline */}
          <div data-timeline="true" className="card" style={{
            marginBottom: 'var(--space-10)',
            padding: 'var(--space-8)'
          }}>
            <h3 style={{ 
              marginBottom: 'var(--space-6)', 
              color: 'var(--text-primary)', 
              fontSize: 'var(--font-size-xl)',
              fontWeight: 'var(--font-weight-semibold)',
              letterSpacing: 0
            }}>
              Timeline Editor
            </h3>
            
            <PremiumTimeline
              videoDuration={videoDuration}
              startTime={startTime}
              endTime={endTime}
              onTimeChange={(newStart, newEnd) => {
                handleTimelineChange(newStart, newEnd);
                if (formData.url && (newStart !== startTime || newEnd !== endTime)) {
                  setShowPreview(true);
                  // Auto-generate preview when timeline changes (with debounce)
                  setTimeout(() => {
                    if (showPreview) {
                      generateVideoPreview();
                    }
                  }, 1000);
                }
              }}
              hooks={hooks?.hooks || []}
              onHookSelect={handleTimelineHookSelect}
              disabled={!!trimJobId}
            />
            
            <div style={{ 
              marginTop: '20px', 
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '16px',
              fontSize: '14px', 
              color: 'var(--dark-gray)' 
            }}>
              <div>
                <strong>Selected Range:</strong><br />
                {formatSecondsToTime(startTime)} - {formatSecondsToTime(endTime)}
              </div>
              <div>
                <strong>Clip Duration:</strong><br />
                {formatTime(endTime - startTime)}
              </div>
              <div>
                <strong>Video Length:</strong><br />
                {formatTime(videoDuration)}
              </div>
            </div>
          </div>

          {/* Export Options */}
          <div className="card" style={{ 
            marginBottom: 'var(--space-10)', 
            padding: 'var(--space-8)'
          }}>
            <h4 style={{ 
              marginBottom: 'var(--space-5)', 
              color: 'var(--text-primary)', 
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-semibold)'
            }}>
              Export Settings
            </h4>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  cursor: 'pointer', 
                  fontSize: 'var(--font-size-base)',
                  fontWeight: 'var(--font-weight-medium)',
                  color: 'var(--text-primary)',
                  padding: 'var(--space-4)',
                  backgroundColor: 'var(--surface)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = 'var(--primary)';
                  e.target.style.backgroundColor = 'var(--primary-subtle)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = 'var(--border)';
                  e.target.style.backgroundColor = 'var(--surface)';
                }}>
                  <input
                    type="checkbox"
                    name="verticalFormat"
                    checked={formData.verticalFormat}
                    onChange={handleInputChange}
                    className="focus-ring"
                    style={{ 
                      marginRight: 'var(--space-3)', 
                      transform: 'scale(1.3)',
                      accentColor: 'var(--primary)'
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 'var(--font-weight-semibold)', marginBottom: '2px' }}>Vertical format (9:16)</div>
                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>Optimized for mobile and social platforms</div>
                  </div>
                </label>

                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  cursor: 'pointer', 
                  fontSize: 'var(--font-size-base)',
                  fontWeight: 'var(--font-weight-medium)',
                  color: 'var(--text-primary)',
                  padding: 'var(--space-4)',
                  backgroundColor: 'var(--surface)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = 'var(--primary)';
                  e.target.style.backgroundColor = 'var(--primary-subtle)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = 'var(--border)';
                  e.target.style.backgroundColor = 'var(--surface)';
                }}>
                  <input
                    type="checkbox"
                    name="addSubtitles"
                    checked={formData.addSubtitles}
                    onChange={handleInputChange}
                    className="focus-ring"
                    style={{ 
                      marginRight: 'var(--space-3)', 
                      transform: 'scale(1.3)',
                      accentColor: 'var(--primary)'
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 'var(--font-weight-semibold)', marginBottom: '2px' }}>Automatic subtitles</div>
                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>AI-generated captions for accessibility</div>
                  </div>
                </label>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!!trimJobId}
            style={{
              width: '100%',
              padding: '20px',
              backgroundColor: trimJobId ? 'var(--dark-gray)' : 'var(--primary)',
              color: trimJobId ? 'var(--dark-gray)' : 'var(--text-primary)',
              border: 'none',
              borderRadius: '12px',
              fontSize: '18px',
              fontWeight: '700',
              cursor: trimJobId ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              letterSpacing: '-0.01em',
              fontFamily: 'inherit'
            }}
            onMouseEnter={(e) => {
              if (!trimJobId) {
                e.target.style.backgroundColor = 'var(--primary-hover)';
              }
            }}
            onMouseLeave={(e) => {
              if (!trimJobId) {
                e.target.style.backgroundColor = 'var(--primary)';
              }
            }}
          >
            {trimJobId ? 'Processing Video...' : 'Start Processing'}
          </button>

          {usage && (
            <p style={{ textAlign: 'center', fontSize: '13px', color: 'var(--dark-gray)', marginTop: '12px' }}>
              Videos processed: {usage.current_trims} / {usage.trims_limit === -1 ? '∞' : usage.trims_limit}
            </p>
          )}
        </form>

        {/* Show trim job progress */}
        {trimJobId && <ProgressIndicator job={trimJob} type="trim" />}

        {/* Error Messages */}
        {error && (
          <div style={{
            marginTop: '24px',
            padding: '20px',
            backgroundColor: 'var(--dark-gray)',
            border: '1px solid var(--text-primary)',
            borderRadius: '12px',
            color: 'var(--text-primary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ fontWeight: '500' }}>
                {error}
              </div>
              <button
                onClick={() => setError(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: 'var(--text-primary)',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Success Result */}
        {trimJob?.jobStatus?.status === 'completed' && (
          <div style={{
            marginTop: '32px',
            padding: '32px',
            backgroundColor: 'var(--surface)',
            border: '2px solid var(--primary)',
            borderRadius: '16px'
          }}>
            <h3 style={{ 
              color: 'var(--text-primary)', 
              marginBottom: '24px', 
              fontSize: '22px',
              fontWeight: '600',
              letterSpacing: '-0.02em'
            }}>
              Video Ready
            </h3>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px',
              marginBottom: '24px'
            }}>
              {trimJob.jobStatus.result?.original_duration && (
                <div style={{ 
                  padding: '16px', 
                  backgroundColor: 'var(--dark-gray)', 
                  borderRadius: '8px',
                  border: '1px solid var(--surface)'
                }}>
                  <div style={{ fontSize: '13px', color: 'var(--dark-gray)', fontWeight: '500' }}>Original Duration</div>
                  <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
                    {formatTime(trimJob.jobStatus.result.original_duration)}
                  </div>
                </div>
              )}
              
              <div style={{ 
                padding: '16px', 
                backgroundColor: 'var(--dark-gray)', 
                borderRadius: '8px',
                border: '1px solid var(--surface)'
              }}>
                <div style={{ fontSize: '13px', color: 'var(--dark-gray)', fontWeight: '500' }}>Trimmed Duration</div>
                <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  {formatTime(endTime - startTime)}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <button
                onClick={handleDownload}
                style={{
                  flex: '1',
                  minWidth: '200px',
                  padding: '16px 24px',
                  backgroundColor: 'var(--primary)',
                  color: 'var(--dark-gray)',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  fontFamily: 'inherit'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--primary-hover)'}
                onMouseLeave={(e) => e.target.style.backgroundColor = 'var(--primary)'}
              >
                Download Video
              </button>
              
              <button
                onClick={() => {
                  trimJob.cleanup();
                  setTrimJobId(null);
                }}
                style={{
                  padding: '16px 24px',
                  backgroundColor: 'transparent',
                  color: 'var(--dark-gray)',
                  border: '2px solid var(--surface)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  fontWeight: '500',
                  transition: 'all 0.2s ease',
                  fontFamily: 'inherit'
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = 'var(--dark-gray)';
                  e.target.style.color = 'var(--dark-gray)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = 'var(--surface)';
                  e.target.style.color = 'var(--dark-gray)';
                }}
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default PremiumVideoProcessor;