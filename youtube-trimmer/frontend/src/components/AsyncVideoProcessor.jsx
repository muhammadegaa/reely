import React, { useState } from 'react';
import { jobTracker, useJobTracker } from '../services/jobTracker';\nimport VideoTimeline from './VideoTimeline';

const AsyncVideoProcessor = ({ usage, subscription, onUsageUpdate }) => {
  const [formData, setFormData] = useState({
    url: '',
    startTime: '',
    endTime: '',
    verticalFormat: false,
    addSubtitles: false
  });
  
  // Timeline state
  const [videoDuration, setVideoDuration] = useState(100); // Default duration
  const [useTimeline, setUseTimeline] = useState(true);

  // Job tracking states
  const [trimJobId, setTrimJobId] = useState(null);
  const [hooksJobId, setHooksJobId] = useState(null);
  const [hooks, setHooks] = useState(null);
  const [error, setError] = useState(null);
  const [aiProvider, setAiProvider] = useState('openai');

  // Use job tracker hooks
  const trimJob = useJobTracker(trimJobId);
  const hooksJob = useJobTracker(hooksJobId);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    if (!formData.url) {
      setError('Please enter a YouTube URL');
      return false;
    }
    if (!formData.startTime) {
      setError('Please enter a start time');
      return false;
    }
    if (!formData.endTime) {
      setError('Please enter an end time');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    if (!validateForm()) {
      return;
    }

    try {
      // Create form data for async processing
      const asyncFormData = new FormData();
      asyncFormData.append('url', formData.url);
      asyncFormData.append('start_time', formData.startTime);
      asyncFormData.append('end_time', formData.endTime);
      asyncFormData.append('vertical_format', formData.verticalFormat);
      asyncFormData.append('add_subtitles', formData.addSubtitles);

      console.log('Starting async trim job...');
      const jobData = await jobTracker.startTrimJob(asyncFormData);
      setTrimJobId(jobData.job_id);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_trims: usage.current_trims + 1
        });
      }
    } catch (err) {
      console.error('Error starting trim job:', err);
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
      console.log('Starting async hooks job...');
      const jobData = await jobTracker.startHooksJob(formData.url, aiProvider);
      setHooksJobId(jobData.job_id);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_hooks: usage.current_hooks + 1
        });
      }
    } catch (err) {
      console.error('Error starting hooks job:', err);
      let errorMessage = 'Failed to start AI analysis. Please try again.';
      
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message?.includes('Network Error')) {
        errorMessage = 'Network error. Please check your connection and try again.';
      }
      
      setError(errorMessage);
    }
  };

  // Handle hooks job completion
  React.useEffect(() => {
    if (hooksJob?.jobStatus?.status === 'completed' && hooksJob.jobStatus.result) {
      setHooks(hooksJob.jobStatus.result);
      setHooksJobId(null); // Clear job ID to stop polling
    } else if (hooksJob?.jobStatus?.status === 'failed') {
      setError(hooksJob.jobStatus.error || 'Hook analysis failed');
      setHooksJobId(null);
    }
  }, [hooksJob?.jobStatus]);

  const handleUseHook = (hook) => {
    const formatTime = (seconds) => {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    setFormData(prev => ({
      ...prev,
      startTime: formatTime(hook.start),
      endTime: formatTime(hook.end)
    }));

    setHooks(null);
    setError(null);
  };

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

  // Progress bar component
  const ProgressBar = ({ job, type }) => {
    if (!job?.jobStatus) return null;

    const { status, progress, message, estimatedTimeRemaining } = job.jobStatus;
    
    return (
      <div style={{
        marginTop: '15px',
        padding: '20px',
        backgroundColor: '#E3F2FD',
        border: '2px solid #2196F3',
        borderRadius: '8px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h4 style={{ margin: 0, color: '#1565C0' }}>
            {type === 'trim' ? '🎬 Processing Video' : '🤖 AI Analysis'}
          </h4>
          <span style={{ fontSize: '14px', color: '#1565C0' }}>
            {progress}%
          </span>
        </div>

        {/* Progress bar */}
        <div style={{
          width: '100%',
          height: '12px',
          backgroundColor: '#BBDEFB',
          borderRadius: '6px',
          overflow: 'hidden',
          marginBottom: '10px'
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            backgroundColor: '#2196F3',
            borderRadius: '6px',
            transition: 'width 0.3s ease'
          }} />
        </div>

        {/* Status message */}
        <div style={{ fontSize: '14px', color: '#1565C0', marginBottom: '8px' }}>
          <strong>Status:</strong> {message}
        </div>

        {/* Time estimate */}
        {estimatedTimeRemaining && (
          <div style={{ fontSize: '13px', color: '#1976D2' }}>
            <strong>Estimated time remaining:</strong> {job.formatTime(estimatedTimeRemaining)}
          </div>
        )}

        {/* Processing tips */}
        {status === 'downloading' && (
          <div style={{ fontSize: '12px', color: '#1976D2', marginTop: '8px', fontStyle: 'italic' }}>
            💡 Downloading video at optimal quality for processing...
          </div>
        )}
        {status === 'transcribing' && (
          <div style={{ fontSize: '12px', color: '#1976D2', marginTop: '8px', fontStyle: 'italic' }}>
            💡 Using segment-only transcription for faster processing...
          </div>
        )}
        {status === 'processing' && type === 'hooks' && (
          <div style={{ fontSize: '12px', color: '#1976D2', marginTop: '8px', fontStyle: 'italic' }}>
            💡 AI is analyzing video content for engaging moments...
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ color: '#37353E', margin: 0 }}>YouTube Video Trimmer</h2>
        <span style={{ 
          marginLeft: '15px',
          padding: '4px 12px',
          backgroundColor: '#4CAF50',
          color: 'white',
          borderRadius: '12px',
          fontSize: '12px',
          fontWeight: 'bold'
        }}>
          ⚡ ASYNC - NO TIMEOUTS!
        </span>
      </div>

      <form onSubmit={handleSubmit} style={{ marginBottom: '30px' }}>
        {/* YouTube URL Input */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#44444E' }}>
            YouTube URL *
          </label>
          <input
            type="url"
            name="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://www.youtube.com/watch?v=..."
            style={{
              width: '100%',
              padding: '12px',
              border: '2px solid #715A5A',
              borderRadius: '6px',
              fontSize: '16px',
              backgroundColor: '#D3DAD9'
            }}
            required
          />
        </div>

        {/* AI Hook Detection Section */}
        <div style={{
          marginBottom: '20px',
          padding: '20px',
          backgroundColor: '#D3DAD9',
          border: '2px solid #715A5A',
          borderRadius: '8px'
        }}>
          <h3 style={{ marginBottom: '15px', color: '#37353E' }}>
            🤖 AI Hook Detection (Async Processing)
          </h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#44444E' }}>
              AI Provider
            </label>
            <select
              value={aiProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              style={{
                padding: '8px 12px',
                border: '1px solid #715A5A',
                borderRadius: '4px',
                marginRight: '15px',
                backgroundColor: 'white'
              }}
            >
              <option value="openai">OpenAI (GPT-4)</option>
              <option value="anthropic">Anthropic (Claude)</option>
            </select>

            <button
              type="button"
              onClick={handleAutoHooks}
              disabled={!!hooksJobId || !formData.url}
              style={{
                padding: '10px 20px',
                backgroundColor: hooksJobId ? '#715A5A' : '#37353E',
                color: '#D3DAD9',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: hooksJobId || !formData.url ? 'not-allowed' : 'pointer'
              }}
            >
              {hooksJobId ? 'Analyzing Video...' : 'Find Hook Points'}
            </button>
          </div>

          {usage && (
            <p style={{ fontSize: '12px', color: '#44444E', margin: 0 }}>
              Hook detections used: {usage.current_hooks} / {usage.hooks_limit === -1 ? '∞' : usage.hooks_limit}
            </p>
          )}
        </div>

        {/* Show hooks job progress */}
        {hooksJobId && <ProgressBar job={hooksJob} type="hooks" />}

        {/* Time Inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#44444E' }}>
              Start Time *
            </label>
            <input
              type="text"
              name="startTime"
              value={formData.startTime}
              onChange={handleInputChange}
              placeholder="0:30 or 00:30"
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #715A5A',
                borderRadius: '6px',
                fontSize: '16px',
                backgroundColor: '#D3DAD9'
              }}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#44444E' }}>
              End Time *
            </label>
            <input
              type="text"
              name="endTime"
              value={formData.endTime}
              onChange={handleInputChange}
              placeholder="1:30 or 01:30"
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #715A5A',
                borderRadius: '6px',
                fontSize: '16px',
                backgroundColor: '#D3DAD9'
              }}
              required
            />
          </div>
        </div>

        {/* Options */}
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#D3DAD9', borderRadius: '6px' }}>
          <h4 style={{ marginBottom: '10px', color: '#37353E' }}>Export Options</h4>
          
          <label style={{ display: 'flex', alignItems: 'center', marginBottom: '10px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              name="verticalFormat"
              checked={formData.verticalFormat}
              onChange={handleInputChange}
              style={{ marginRight: '8px', transform: 'scale(1.2)' }}
            />
            <span style={{ color: '#44444E' }}>Convert to vertical format (9:16)</span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              name="addSubtitles"
              checked={formData.addSubtitles}
              onChange={handleInputChange}
              style={{ marginRight: '8px', transform: 'scale(1.2)' }}
            />
            <span style={{ color: '#44444E' }}>Add subtitles (segment-only transcription)</span>
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!!trimJobId}
          style={{
            width: '100%',
            padding: '15px',
            backgroundColor: trimJobId ? '#715A5A' : '#37353E',
            color: '#D3DAD9',
            border: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: '600',
            cursor: trimJobId ? 'not-allowed' : 'pointer'
          }}
        >
          {trimJobId ? 'Processing Video...' : '🚀 Start Async Processing'}
        </button>

        {usage && (
          <p style={{ textAlign: 'center', fontSize: '12px', color: '#44444E', marginTop: '10px' }}>
            Video trims used: {usage.current_trims} / {usage.trims_limit === -1 ? '∞' : usage.trims_limit}
          </p>
        )}
      </form>

      {/* Show trim job progress */}
      {trimJobId && <ProgressBar job={trimJob} type="trim" />}

      {/* Error Messages */}
      {error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#ffebee',
          border: '2px solid #f44336',
          borderRadius: '6px',
          marginBottom: '20px',
          color: '#c62828'
        }}>
          <strong>Error:</strong> {error}
          <button
            onClick={() => setError(null)}
            style={{
              float: 'right',
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: '#c62828'
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Hook Results */}
      {hooks && (
        <div style={{
          padding: '20px',
          backgroundColor: '#e8f5e8',
          border: '2px solid #4caf50',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#2e7d32', marginBottom: '15px' }}>
            🎯 Found {hooks.total_hooks} Hook Point{hooks.total_hooks !== 1 ? 's' : ''}
          </h3>
          
          {hooks.hooks.map((hook, index) => {
            const duration = hook.end - hook.start;
            return (
              <div key={index} style={{
                padding: '15px',
                backgroundColor: 'white',
                border: '1px solid #81c784',
                borderRadius: '6px',
                marginBottom: '10px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h4 style={{ margin: '0 0 5px 0', color: '#2e7d32' }}>{hook.title}</h4>
                    <p style={{ margin: '0 0 5px 0', color: '#555', fontSize: '14px' }}>
                      {formatTime(hook.start)} - {formatTime(hook.end)} ({duration}s)
                    </p>
                    {hook.reason && (
                      <p style={{ margin: 0, color: '#777', fontSize: '12px', fontStyle: 'italic' }}>
                        {hook.reason}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleUseHook(hook)}
                    style={{
                      padding: '8px 15px',
                      backgroundColor: '#37353E',
                      color: '#D3DAD9',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    Use This Hook
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Success Result with Download */}
      {trimJob?.jobStatus?.status === 'completed' && (
        <div style={{
          padding: '20px',
          backgroundColor: '#e8f5e8',
          border: '2px solid #4caf50',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#2e7d32', marginBottom: '15px' }}>🎉 Video Processed Successfully!</h3>
          
          <div style={{ marginBottom: '15px' }}>
            {trimJob.jobStatus.result?.original_duration && (
              <p style={{ margin: '5px 0', color: '#2e7d32' }}>
                <strong>Original Duration:</strong> {formatTime(trimJob.jobStatus.result.original_duration)}
              </p>
            )}
            {trimJob.jobStatus.result?.trimmed_duration && (
              <p style={{ margin: '5px 0', color: '#2e7d32' }}>
                <strong>Trimmed Duration:</strong> {formatTime(trimJob.jobStatus.result.trimmed_duration)}
              </p>
            )}
          </div>

          <button
            onClick={handleDownload}
            style={{
              width: '100%',
              padding: '15px',
              backgroundColor: '#37353E',
              color: '#D3DAD9',
              border: 'none',
              borderRadius: '8px',
              fontSize: '18px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            📥 Download Trimmed Video
          </button>
          
          <button
            onClick={() => {
              trimJob.cleanup();
              setTrimJobId(null);
            }}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: 'transparent',
              color: '#666',
              border: '1px solid #ccc',
              borderRadius: '6px',
              fontSize: '14px',
              cursor: 'pointer',
              marginTop: '10px'
            }}
          >
            🗑️ Clean Up Files
          </button>
        </div>
      )}
    </div>
  );
};

export default AsyncVideoProcessor;