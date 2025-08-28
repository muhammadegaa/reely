import React, { useState } from 'react';
import { videoAPI } from '../services/api';

const VideoProcessor = ({ usage, subscription, onUsageUpdate }) => {
  const [formData, setFormData] = useState({
    url: '',
    startTime: '',
    endTime: '',
    verticalFormat: false,
    addSubtitles: false
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [hooks, setHooks] = useState(null);
  const [hooksLoading, setHooksLoading] = useState(false);
  const [hooksError, setHooksError] = useState(null);
  const [aiProvider, setAiProvider] = useState('openai');

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
    setResult(null);
    
    console.log('Form submitted with data:', formData);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('url', formData.url);
      formDataToSend.append('start_time', formData.startTime);
      formDataToSend.append('end_time', formData.endTime);
      formDataToSend.append('vertical_format', formData.verticalFormat);
      formDataToSend.append('add_subtitles', formData.addSubtitles);

      console.log('Sending request to backend...');
      const data = await videoAPI.trim(formDataToSend);
      console.log('Received response:', data);
      setResult(data);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_trims: usage.current_trims + 1
        });
      }
    } catch (err) {
      console.error('Error processing video:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to process video. Please try again.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoHooks = async () => {
    setHooksError(null);
    setHooks(null);
    
    console.log('Auto hooks clicked with URL:', formData.url);
    
    if (!formData.url) {
      setHooksError('Please enter a YouTube URL first');
      return;
    }

    setHooksLoading(true);

    try {
      console.log('Calling auto-hooks API...');
      const data = await videoAPI.autoHooks(formData.url, aiProvider);
      console.log('Auto hooks response:', data);
      setHooks(data);
      
      if (onUsageUpdate && usage) {
        onUsageUpdate({
          ...usage,
          current_hooks: usage.current_hooks + 1
        });
      }
    } catch (err) {
      console.error('Error getting auto hooks:', err);
      let errorMessage = 'Failed to analyze video. Please try again.';
      
      // Handle specific error cases
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = 'Video analysis timed out. This can happen with very long videos or slow network connections. The system processes long videos using smart sampling to reduce processing time. Please try again, or consider using shorter video segments.';
      } else if (err.response?.status === 500) {
        errorMessage = 'Server error: Please check that your OpenAI API key is valid and has sufficient credits. For very long videos, processing may take several minutes.';
      } else if (err.response?.status === 429) {
        errorMessage = 'Rate limit exceeded. Please wait a moment and try again.';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message?.includes('Network Error')) {
        errorMessage = 'Network error. Please check your connection and try again.';
      }
      
      setHooksError(errorMessage);
    } finally {
      setHooksLoading(false);
    }
  };

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
    setHooksError(null);
  };

  const handleDownload = () => {
    if (result?.download_id) {
      window.open(videoAPI.downloadVideo(result.download_id), '_blank');
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

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h2 style={{ marginBottom: '20px', color: '#37353E' }}>YouTube Video Trimmer</h2>

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
          <h3 style={{ marginBottom: '15px', color: '#37353E' }}>AI Hook Detection</h3>
          
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
              disabled={hooksLoading || !formData.url}
              style={{
                padding: '10px 20px',
                backgroundColor: hooksLoading ? '#715A5A' : '#37353E',
                color: '#D3DAD9',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: hooksLoading || !formData.url ? 'not-allowed' : 'pointer'
              }}
            >
              {hooksLoading ? 'Analyzing video (this may take several minutes for long videos)...' : 'Find Hook Points'}
            </button>
          </div>

          {hooksLoading && (
            <div style={{
              marginTop: '15px',
              padding: '15px',
              backgroundColor: '#E8F4FD',
              border: '1px solid #B3D9FF',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#1E40AF'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>Processing your video...</div>
              <div style={{ fontSize: '13px', lineHeight: '1.4' }}>
                • Long videos use smart sampling for faster processing<br/>
                • We analyze key segments instead of the entire video<br/>
                • Processing time: ~2-5 minutes for videos up to 1 hour<br/>
                • Please keep this tab open during processing
              </div>
            </div>
          )}
          
          {usage && (
            <p style={{ fontSize: '12px', color: '#44444E', margin: 0 }}>
              Hook detections used: {usage.current_hooks} / {usage.hooks_limit === -1 ? '∞' : usage.hooks_limit}
            </p>
          )}
        </div>

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
            <span style={{ color: '#44444E' }}>Add subtitles</span>
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '15px',
            backgroundColor: loading ? '#715A5A' : '#37353E',
            color: '#D3DAD9',
            border: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Processing Video...' : 'Trim Video'}
        </button>

        {usage && (
          <p style={{ textAlign: 'center', fontSize: '12px', color: '#44444E', marginTop: '10px' }}>
            Video trims used: {usage.current_trims} / {usage.trims_limit === -1 ? '∞' : usage.trims_limit}
          </p>
        )}
      </form>

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

      {hooksError && (
        <div style={{
          padding: '15px',
          backgroundColor: '#ffebee',
          border: '2px solid #f44336',
          borderRadius: '6px',
          marginBottom: '20px',
          color: '#c62828'
        }}>
          <strong>AI Error:</strong> {hooksError}
          <button
            onClick={() => setHooksError(null)}
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
            Found {hooks.total_hooks} Hook Point{hooks.total_hooks !== 1 ? 's' : ''}
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

      {/* Success Result */}
      {result && (
        <div style={{
          padding: '20px',
          backgroundColor: '#e8f5e8',
          border: '2px solid #4caf50',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#2e7d32', marginBottom: '15px' }}>Video Processed Successfully!</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <p style={{ margin: '5px 0', color: '#2e7d32' }}>
              <strong>Original Duration:</strong> {formatTime(result.original_duration)}
            </p>
            <p style={{ margin: '5px 0', color: '#2e7d32' }}>
              <strong>Trimmed Duration:</strong> {formatTime(result.trimmed_duration)}
            </p>
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
            Download Trimmed Video
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoProcessor;