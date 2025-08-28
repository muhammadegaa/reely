// Job tracking service for async video processing
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

class JobTracker {
  constructor() {
    this.activeJobs = new Map();
    this.pollingIntervals = new Map();
  }

  // Start a trim job
  async startTrimJob(formData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/trim`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000, // 30 seconds for job creation (not processing!)
      });
      
      const jobData = response.data;
      this.activeJobs.set(jobData.job_id, {
        ...jobData,
        type: 'trim',
        startTime: Date.now()
      });
      
      return jobData;
    } catch (error) {
      console.error('Failed to start trim job:', error);
      throw error;
    }
  }

  // Start hooks job
  async startHooksJob(url, aiProvider) {
    try {
      const formData = new FormData();
      formData.append('url', url);
      formData.append('ai_provider', aiProvider);
      
      const response = await axios.post(`${API_BASE_URL}/auto-hooks`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000, // 30 seconds for job creation
      });
      
      const jobData = response.data;
      this.activeJobs.set(jobData.job_id, {
        ...jobData,
        type: 'hooks',
        startTime: Date.now()
      });
      
      return jobData;
    } catch (error) {
      console.error('Failed to start hooks job:', error);
      throw error;
    }
  }

  // Poll job status
  async pollJobStatus(jobId, onProgress, onComplete, onError) {
    const pollInterval = 2000; // Poll every 2 seconds
    
    const poll = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/job/${jobId}`, {
          timeout: 10000
        });
        
        const jobData = response.data;
        
        // Update active jobs
        if (this.activeJobs.has(jobId)) {
          this.activeJobs.set(jobId, {
            ...this.activeJobs.get(jobId),
            ...jobData,
            lastUpdate: Date.now()
          });
        }
        
        // Call progress callback
        if (onProgress) {
          const estimatedTimeRemaining = this.estimateTimeRemaining(jobId, jobData);
          onProgress({
            ...jobData,
            estimatedTimeRemaining
          });
        }
        
        // Check if job is complete
        if (jobData.status === 'completed') {
          this.stopPolling(jobId);
          if (onComplete) {
            onComplete(jobData);
          }
        } else if (jobData.status === 'failed') {
          this.stopPolling(jobId);
          if (onError) {
            onError(jobData.error || 'Job failed');
          }
        }
        
      } catch (error) {
        console.error('Failed to poll job status:', error);
        // Don't stop polling on network errors, retry
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          console.log('Polling timeout, retrying...');
        } else {
          this.stopPolling(jobId);
          if (onError) {
            onError(error.message || 'Failed to check job status');
          }
        }
      }
    };
    
    // Start polling immediately
    await poll();
    
    // Continue polling if job is not complete
    const interval = setInterval(poll, pollInterval);
    this.pollingIntervals.set(jobId, interval);
    
    // Auto-stop polling after 30 minutes (safety)
    setTimeout(() => {
      if (this.pollingIntervals.has(jobId)) {
        console.warn(`Job ${jobId} auto-stopped after 30 minutes`);
        this.stopPolling(jobId);
        if (onError) {
          onError('Job exceeded maximum processing time');
        }
      }
    }, 30 * 60 * 1000);
  }

  // Estimate time remaining based on progress
  estimateTimeRemaining(jobId, jobData) {
    const job = this.activeJobs.get(jobId);
    if (!job || !job.startTime || jobData.progress <= 0) {
      return null;
    }
    
    const elapsed = Date.now() - job.startTime;
    const progressRate = jobData.progress / elapsed;
    const remaining = (100 - jobData.progress) / progressRate;
    
    return Math.max(0, Math.round(remaining / 1000)); // seconds
  }

  // Stop polling for a job
  stopPolling(jobId) {
    if (this.pollingIntervals.has(jobId)) {
      clearInterval(this.pollingIntervals.get(jobId));
      this.pollingIntervals.delete(jobId);
    }
    
    // Keep job data for download, but mark as inactive
    if (this.activeJobs.has(jobId)) {
      const job = this.activeJobs.get(jobId);
      this.activeJobs.set(jobId, { ...job, polling: false });
    }
  }

  // Get download URL
  getDownloadUrl(jobId) {
    return `${API_BASE_URL}/download/${jobId}`;
  }

  // Cleanup job
  async cleanupJob(jobId) {
    try {
      await axios.delete(`${API_BASE_URL}/cleanup/${jobId}`);
      this.stopPolling(jobId);
      this.activeJobs.delete(jobId);
    } catch (error) {
      console.error('Failed to cleanup job:', error);
    }
  }

  // Get all active jobs
  getActiveJobs() {
    return Array.from(this.activeJobs.values());
  }

  // Format time for display
  formatTime(seconds) {
    if (!seconds || seconds <= 0) return null;
    
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${mins}m`;
    }
  }
}

// Create global instance
export const jobTracker = new JobTracker();

// React hook for using job tracker
import { useState, useEffect } from 'react';

export const useJobTracker = (jobId) => {
  const [jobStatus, setJobStatus] = useState(null);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    setIsPolling(true);

    const handleProgress = (data) => {
      setJobStatus(data);
    };

    const handleComplete = (data) => {
      setJobStatus(data);
      setIsPolling(false);
    };

    const handleError = (error) => {
      setJobStatus(prev => ({ ...prev, error, status: 'failed' }));
      setIsPolling(false);
    };

    jobTracker.pollJobStatus(jobId, handleProgress, handleComplete, handleError);

    return () => {
      jobTracker.stopPolling(jobId);
      setIsPolling(false);
    };
  }, [jobId]);

  return {
    jobStatus,
    isPolling,
    downloadUrl: jobId ? jobTracker.getDownloadUrl(jobId) : null,
    cleanup: () => jobTracker.cleanupJob(jobId),
    formatTime: jobTracker.formatTime
  };
};