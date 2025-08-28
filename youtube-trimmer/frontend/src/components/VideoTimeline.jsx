import React, { useState, useRef, useEffect, useCallback } from 'react';

const VideoTimeline = ({
  videoDuration = 100, // Total video duration in seconds
  startTime = 0,
  endTime = 30,
  onTimeChange,
  hooks = [],
  onHookSelect,
  disabled = false
}) => {
  const timelineRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null); // 'start', 'end', 'range'
  const [timelineWidth, setTimelineWidth] = useState(0);

  // Update timeline width on resize
  useEffect(() => {
    const updateWidth = () => {
      if (timelineRef.current) {
        setTimelineWidth(timelineRef.current.offsetWidth - 40); // Account for padding
      }
    };

    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Convert time to pixel position
  const timeToPixel = useCallback((time) => {
    if (!timelineWidth || !videoDuration) return 0;
    return (time / videoDuration) * timelineWidth;
  }, [timelineWidth, videoDuration]);

  // Convert pixel position to time
  const pixelToTime = useCallback((pixel) => {
    if (!timelineWidth || !videoDuration) return 0;
    const time = (pixel / timelineWidth) * videoDuration;
    return Math.max(0, Math.min(videoDuration, time));
  }, [timelineWidth, videoDuration]);

  // Handle mouse down on handles
  const handleMouseDown = (e, type) => {
    if (disabled) return;
    e.preventDefault();
    setIsDragging(true);
    setDragType(type);
  };

  // Handle mouse move (dragging)
  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !timelineRef.current || !dragType) return;

    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - 20; // Account for padding
    const newTime = pixelToTime(x);

    if (dragType === 'start') {
      const newStart = Math.max(0, Math.min(newTime, endTime - 1));
      onTimeChange?.(newStart, endTime);
    } else if (dragType === 'end') {
      const newEnd = Math.max(startTime + 1, Math.min(newTime, videoDuration));
      onTimeChange?.(startTime, newEnd);
    } else if (dragType === 'range') {
      const duration = endTime - startTime;
      const newStart = Math.max(0, Math.min(newTime - duration / 2, videoDuration - duration));
      const newEnd = newStart + duration;
      onTimeChange?.(newStart, newEnd);
    }
  }, [isDragging, dragType, pixelToTime, startTime, endTime, videoDuration, onTimeChange]);

  // Handle mouse up (stop dragging)
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragType(null);
  }, []);

  // Add global mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Handle timeline click (set position)
  const handleTimelineClick = (e) => {
    if (disabled || isDragging) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - 20;
    const clickTime = pixelToTime(x);
    
    // Snap to closest handle
    const startDist = Math.abs(clickTime - startTime);
    const endDist = Math.abs(clickTime - endTime);
    
    if (startDist < endDist) {
      onTimeChange?.(clickTime, endTime);
    } else {
      onTimeChange?.(startTime, clickTime);
    }
  };

  // Handle hook click
  const handleHookClick = (hook) => {
    if (disabled) return;
    onHookSelect?.(hook);
  };

  // Format time display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Touch event handlers for mobile
  const handleTouchStart = (e, type) => {
    if (disabled) return;
    e.preventDefault();
    setIsDragging(true);
    setDragType(type);
  };

  const handleTouchMove = useCallback((e) => {
    if (!isDragging || !timelineRef.current || !dragType) return;
    e.preventDefault();

    const rect = timelineRef.current.getBoundingClientRect();
    const touch = e.touches[0];
    const x = touch.clientX - rect.left - 20;
    const newTime = pixelToTime(x);

    if (dragType === 'start') {
      const newStart = Math.max(0, Math.min(newTime, endTime - 1));
      onTimeChange?.(newStart, endTime);
    } else if (dragType === 'end') {
      const newEnd = Math.max(startTime + 1, Math.min(newTime, videoDuration));
      onTimeChange?.(startTime, newEnd);
    }
  }, [isDragging, dragType, pixelToTime, startTime, endTime, videoDuration, onTimeChange]);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    setDragType(null);
  }, []);

  // Touch event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('touchmove', handleTouchMove, { passive: false });
      document.addEventListener('touchend', handleTouchEnd);
      return () => {
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isDragging, handleTouchMove, handleTouchEnd]);

  const startPixel = timeToPixel(startTime);
  const endPixel = timeToPixel(endTime);
  const selectionWidth = endPixel - startPixel;

  return (
    <div style={{ marginBottom: '20px' }}>
      {/* Time display */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        marginBottom: '10px',
        fontSize: '14px',
        fontWeight: '500',
        color: '#44444E'
      }}>
        <div>
          <span style={{ color: '#2196F3' }}>Start: {formatTime(startTime)}</span>
          <span style={{ marginLeft: '20px', color: '#FF9800' }}>
            End: {formatTime(endTime)}
          </span>
        </div>
        <div style={{ color: '#4CAF50' }}>
          Duration: {formatTime(endTime - startTime)} / {formatTime(videoDuration)}
        </div>
      </div>

      {/* Timeline container */}
      <div 
        ref={timelineRef}
        onClick={handleTimelineClick}
        style={{
          position: 'relative',
          height: '60px',
          backgroundColor: '#D3DAD9',
          border: '2px solid #715A5A',
          borderRadius: '8px',
          padding: '20px',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          userSelect: 'none'
        }}
      >
        {/* Timeline track */}
        <div style={{
          position: 'absolute',
          top: '25px',
          left: '20px',
          right: '20px',
          height: '10px',
          backgroundColor: '#9E9E9E',
          borderRadius: '5px',
          overflow: 'hidden'
        }}>
          {/* Selection range */}
          <div style={{
            position: 'absolute',
            left: `${startPixel}px`,
            width: `${selectionWidth}px`,
            height: '100%',
            backgroundColor: '#4CAF50',
            borderRadius: '5px',
            transition: isDragging ? 'none' : 'all 0.2s ease',
            boxShadow: '0 2px 4px rgba(76, 175, 80, 0.3)'
          }} />
        </div>

        {/* Hook markers */}
        {hooks.map((hook, index) => {
          const hookStart = timeToPixel(hook.start);
          const hookWidth = timeToPixel(hook.end - hook.start);
          
          return (
            <div
              key={index}
              onClick={(e) => {
                e.stopPropagation();
                handleHookClick(hook);
              }}
              style={{
                position: 'absolute',
                top: '15px',
                left: `${20 + hookStart}px`,
                width: `${Math.max(hookWidth, 8)}px`,
                height: '30px',
                backgroundColor: 'rgba(255, 152, 0, 0.8)',
                borderRadius: '4px',
                cursor: 'pointer',
                border: '2px solid #FF9800',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
                fontWeight: 'bold',
                color: 'white',
                transition: 'transform 0.2s ease',
                zIndex: 10
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = 'scale(1.1)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'scale(1)';
              }}
              title={`${hook.title}\n${formatTime(hook.start)} - ${formatTime(hook.end)}\n${hook.reason || ''}`}
            >
              🎯
            </div>
          );
        })}

        {/* Start handle */}
        <div
          onMouseDown={(e) => handleMouseDown(e, 'start')}
          onTouchStart={(e) => handleTouchStart(e, 'start')}
          style={{
            position: 'absolute',
            top: '10px',
            left: `${20 + startPixel - 8}px`,
            width: '16px',
            height: '40px',
            backgroundColor: '#2196F3',
            borderRadius: '8px',
            cursor: disabled ? 'not-allowed' : 'ew-resize',
            zIndex: 20,
            border: '2px solid white',
            boxShadow: '0 2px 8px rgba(33, 150, 243, 0.4)',
            transition: isDragging && dragType === 'start' ? 'none' : 'transform 0.2s ease',
            transform: isDragging && dragType === 'start' ? 'scale(1.2)' : 'scale(1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            color: 'white',
            fontWeight: 'bold'
          }}
          onMouseEnter={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1)';
          }}
        >
          ▌
        </div>

        {/* End handle */}
        <div
          onMouseDown={(e) => handleMouseDown(e, 'end')}
          onTouchStart={(e) => handleTouchStart(e, 'end')}
          style={{
            position: 'absolute',
            top: '10px',
            left: `${20 + endPixel - 8}px`,
            width: '16px',
            height: '40px',
            backgroundColor: '#FF9800',
            borderRadius: '8px',
            cursor: disabled ? 'not-allowed' : 'ew-resize',
            zIndex: 20,
            border: '2px solid white',
            boxShadow: '0 2px 8px rgba(255, 152, 0, 0.4)',
            transition: isDragging && dragType === 'end' ? 'none' : 'transform 0.2s ease',
            transform: isDragging && dragType === 'end' ? 'scale(1.2)' : 'scale(1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            color: 'white',
            fontWeight: 'bold'
          }}
          onMouseEnter={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1)';
          }}
        >
          ▐
        </div>

        {/* Time ruler (optional) */}
        <div style={{
          position: 'absolute',
          bottom: '5px',
          left: '20px',
          right: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          color: '#666'
        }}>
          <span>0:00</span>
          <span>{formatTime(videoDuration / 2)}</span>
          <span>{formatTime(videoDuration)}</span>
        </div>
      </div>

      {/* Instructions */}
      <div style={{
        fontSize: '12px',
        color: '#666',
        marginTop: '8px',
        textAlign: 'center'
      }}>
        🎬 Drag the blue/orange handles to trim • 🎯 Click orange hook markers to auto-select • Click timeline to set position
      </div>
    </div>
  );
};

export default VideoTimeline;