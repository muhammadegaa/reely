import React, { useState } from 'react';
import { jobTracker, useJobTracker } from '../services/jobTracker';
import VideoTimeline from './VideoTimeline';

const TimelineVideoProcessor = ({ usage, subscription, onUsageUpdate }) => {
  const [formData, setFormData] = useState({
    url: '',
    verticalFormat: false,
    addSubtitles: false
  });
  
  // Timeline state
  const [videoDuration, setVideoDuration] = useState(300); // 5 minutes default
  const [startTime, setStartTime] = useState(30); // 30 seconds
  const [endTime, setEndTime] = useState(60); // 60 seconds
  
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
    if (startTime >= endTime) {
      setError('Start time must be less than end time');
      return false;
    }
    return true;
  };

  // Timeline event handlers
  const handleTimelineChange = (newStart, newEnd) => {
    setStartTime(newStart);
    setEndTime(newEnd);
  };

  const handleTimelineHookSelect = (hook) => {
    setStartTime(hook.start);
    setEndTime(hook.end);
    // Clear hooks display after selection
    setHooks(null);
    setError(null);
  };

  const formatSecondsToTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
      asyncFormData.append('start_time', formatSecondsToTime(startTime));
      asyncFormData.append('end_time', formatSecondsToTime(endTime));
      asyncFormData.append('vertical_format', formData.verticalFormat);
      asyncFormData.append('add_subtitles', formData.addSubtitles);

      console.log('🚀 Starting async trim job...');
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
      console.log('🤖 Starting async hooks job...');
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
        marginTop: '20px',
        padding: '20px',
        backgroundColor: '#E3F2FD',
        border: '2px solid #2196F3',
        borderRadius: '12px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h4 style={{ margin: 0, color: '#1565C0', fontSize: '18px' }}>
            {type === 'trim' ? '🎬 Processing Video' : '🤖 AI Analysis'}
          </h4>
          <div style={{ 
            fontSize: '16px', 
            color: '#1565C0', 
            fontWeight: 'bold',
            backgroundColor: '#BBDEFB',
            padding: '4px 12px',
            borderRadius: '20px'
          }}>
            {progress}%
          </div>
        </div>

        {/* Progress bar */}
        <div style={{
          width: '100%',
          height: '14px',
          backgroundColor: '#BBDEFB',
          borderRadius: '7px',
          overflow: 'hidden',
          marginBottom: '15px'
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #2196F3 0%, #1976D2 100%)',
            borderRadius: '7px',
            transition: 'width 0.3s ease'
          }} />
        </div>

        {/* Status message */}
        <div style={{ fontSize: '15px', color: '#1565C0', marginBottom: '10px' }}>
          <strong>Status:</strong> {message}
        </div>

        {/* Time estimate */}
        {estimatedTimeRemaining && (
          <div style={{ fontSize: '14px', color: '#1976D2', marginBottom: '10px' }}>
            <strong>⏱️ Time remaining:</strong> {job.formatTime(estimatedTimeRemaining)}
          </div>
        )}

        {/* Processing tips */}
        <div style={{ fontSize: '13px', color: '#1976D2', fontStyle: 'italic', backgroundColor: '#E8F4FD', padding: '10px', borderRadius: '8px' }}>
          {status === 'downloading' && '💡 Downloading video at optimal quality...'}
          {status === 'transcribing' && '💡 Using segment-only transcription for faster processing...'}
          {status === 'processing' && type === 'hooks' && '💡 AI analyzing video content for engaging moments...'}
          {status === 'trimming' && '💡 Applying video effects and generating final output...'}
        </div>
      </div>
    );
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '30px' }}>
        <h2 style={{ color: '#37353E', margin: 0, fontSize: '28px' }}>
          🎬 Timeline Video Trimmer
        </h2>
        <div style={{ display: 'flex', gap: '10px', marginLeft: '20px' }}>
          <span style={{ 
            padding: '6px 12px',
            backgroundColor: '#4CAF50',
            color: 'white',
            borderRadius: '16px',
            fontSize: '12px',
            fontWeight: 'bold'
          }}>
            ⚡ NO TIMEOUTS
          </span>
          <span style={{ 
            padding: '6px 12px',
            backgroundColor: '#FF9800',
            color: 'white',
            borderRadius: '16px',
            fontSize: '12px',
            fontWeight: 'bold'
          }}>
            🎯 VISUAL TIMELINE
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ marginBottom: '30px' }}>
        {/* YouTube URL Input */}
        <div style={{ marginBottom: '25px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '10px', 
            fontWeight: '600', 
            color: '#37353E',
            fontSize: '16px'
          }}>
            📺 YouTube URL
          </label>
          <input
            type="url"
            name="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://www.youtube.com/watch?v=..."
            style={{
              width: '100%',
              padding: '14px',
              border: '2px solid #715A5A',
              borderRadius: '8px',
              fontSize: '16px',
              backgroundColor: '#F8F9FA'
            }}
            required
          />
        </div>

        {/* AI Hook Detection */}
        <div style={{
          marginBottom: '25px',
          padding: '25px',
          backgroundColor: '#E8F5E8',
          border: '2px solid #4CAF50',
          borderRadius: '12px'
        }}>
          <h3 style={{ marginBottom: '20px', color: '#2E7D32', fontSize: '20px' }}>
            🤖 AI Hook Detection
          </h3>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '15px' }}>
            <select
              value={aiProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              style={{
                padding: '10px 14px',
                border: '2px solid #4CAF50',
                borderRadius: '6px',
                backgroundColor: 'white',
                fontSize: '14px'
              }}
            >
              <option value="openai">🧠 OpenAI (GPT-4)</option>
              <option value="anthropic">🔮 Anthropic (Claude)</option>
            </select>

            <button
              type="button"
              onClick={handleAutoHooks}
              disabled={!!hooksJobId || !formData.url}
              style={{
                padding: '12px 24px',
                backgroundColor: hooksJobId ? '#9E9E9E' : '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: hooksJobId || !formData.url ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {hooksJobId ? '⚡ Analyzing...' : '🎯 Find Hooks'}
            </button>
          </div>

          {usage && (
            <p style={{ fontSize: '12px', color: '#2E7D32', margin: 0 }}>
              Hooks used: {usage.current_hooks} / {usage.hooks_limit === -1 ? '∞' : usage.hooks_limit}
            </p>
          )}
        </div>

        {/* Show hooks job progress */}
        {hooksJobId && <ProgressBar job={hooksJob} type="hooks" />}

        {/* Video Timeline Component */}
        <div style={{
          marginBottom: '25px',
          padding: '25px',
          backgroundColor: '#F3E5F5',
          border: '2px solid #9C27B0',
          borderRadius: '12px'
        }}>
          <h3 style={{ marginBottom: '20px', color: '#6A1B9A', fontSize: '20px' }}>
            ✂️ Visual Timeline Editor
          </h3>
          
          <VideoTimeline
            videoDuration={videoDuration}
            startTime={startTime}
            endTime={endTime}
            onTimeChange={handleTimelineChange}
            hooks={hooks?.hooks || []}
            onHookSelect={handleTimelineHookSelect}
            disabled={!!trimJobId}
          />
          
          <div style={{ marginTop: '15px', fontSize: '14px', color: '#6A1B9A' }}>
            <div>🎬 <strong>Selected:</strong> {formatSecondsToTime(startTime)} - {formatSecondsToTime(endTime)}</div>
            <div>⏱️ <strong>Duration:</strong> {formatTime(endTime - startTime)}</div>
            <div>📏 <strong>Video Length:</strong> {formatTime(videoDuration)}</div>
          </div>
        </div>

        {/* Export Options */}
        <div style={{ 
          marginBottom: '25px', 
          padding: '20px', 
          backgroundColor: '#FFF3E0', 
          borderRadius: '10px',
          border: '1px solid #FFB74D'
        }}>
          <h4 style={{ marginBottom: '15px', color: '#E65100', fontSize: '18px' }}>⚙️ Export Options</h4>
          
          <div style={{ display: 'flex', gap: '30px' }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '15px' }}>
              <input
                type="checkbox"
                name="verticalFormat"
                checked={formData.verticalFormat}
                onChange={handleInputChange}
                style={{ marginRight: '10px', transform: 'scale(1.2)' }}
              />
              <span style={{ color: '#E65100' }}>📱 Vertical Format (9:16) for TikTok/Instagram</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '15px' }}>
              <input
                type="checkbox"
                name="addSubtitles"
                checked={formData.addSubtitles}
                onChange={handleInputChange}
                style={{ marginRight: '10px', transform: 'scale(1.2)' }}
              />
              <span style={{ color: '#E65100' }}>📝 Add Subtitles (Fast Transcription)</span>
            </label>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!!trimJobId}
          style={{
            width: '100%',
            padding: '18px',
            backgroundColor: trimJobId ? '#9E9E9E' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            fontSize: '20px',
            fontWeight: '700',
            cursor: trimJobId ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: '0 4px 12px rgba(33, 150, 243, 0.3)'
          }}
        >
          {trimJobId ? '⚡ Processing Video...' : '🚀 Start Processing'}
        </button>

        {usage && (
          <p style={{ textAlign: 'center', fontSize: '12px', color: '#666', marginTop: '10px' }}>
            Trims used: {usage.current_trims} / {usage.trims_limit === -1 ? '∞' : usage.trims_limit}
          </p>
        )}
      </form>

      {/* Show trim job progress */}
      {trimJobId && <ProgressBar job={trimJob} type="trim" />}

      {/* Error Messages */}
      {error && (
        <div style={{
          padding: '20px',
          backgroundColor: '#FFEBEE',
          border: '2px solid #F44336',
          borderRadius: '12px',
          marginBottom: '20px',
          color: '#C62828'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>❌ Error:</strong> {error}
            </div>
            <button
              onClick={() => setError(null)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '20px',
                cursor: 'pointer',
                color: '#C62828'
              }}
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Success Result with Download */}
      {trimJob?.jobStatus?.status === 'completed' && (
        <div style={{
          padding: '25px',
          backgroundColor: '#E8F5E8',
          border: '3px solid #4CAF50',
          borderRadius: '12px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#2E7D32', marginBottom: '20px', fontSize: '22px' }}>
            🎉 Video Ready for Download!
          </h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '15px',
            marginBottom: '20px'
          }}>
            {trimJob.jobStatus.result?.original_duration && (
              <div style={{ padding: '10px', backgroundColor: '#F1F8E9', borderRadius: '8px' }}>
                <strong>📹 Original:</strong> {formatTime(trimJob.jobStatus.result.original_duration)}
              </div>
            )}
            {trimJob.jobStatus.result?.trimmed_duration && (
              <div style={{ padding: '10px', backgroundColor: '#F1F8E9', borderRadius: '8px' }}>
                <strong>✂️ Trimmed:</strong> {formatTime(trimJob.jobStatus.result.trimmed_duration)}
              </div>
            )}
            <div style={{ padding: '10px', backgroundColor: '#F1F8E9', borderRadius: '8px' }}>
              <strong>⏱️ Selected:</strong> {formatSecondsToTime(startTime)} - {formatSecondsToTime(endTime)}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '15px' }}>
            <button
              onClick={handleDownload}
              style={{
                flex: 1,
                padding: '15px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '10px',
                fontSize: '18px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              📥 Download Video
            </button>
            
            <button
              onClick={() => {
                trimJob.cleanup();
                setTrimJobId(null);
              }}
              style={{
                padding: '15px 20px',
                backgroundColor: 'transparent',
                color: '#666',
                border: '2px solid #E0E0E0',
                borderRadius: '10px',
                fontSize: '14px',
                cursor: 'pointer'
              }}
            >
              🗑️ Cleanup
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineVideoProcessor;