import React, { useState, useRef, useEffect, useCallback } from 'react';

const PremiumTimeline = ({
  videoDuration = 100,
  startTime = 0,
  endTime = 30,
  onTimeChange,
  hooks = [],
  onHookSelect,
  disabled = false
}) => {
  const timelineRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null);
  const [timelineWidth, setTimelineWidth] = useState(0);

  // Update timeline width on resize
  useEffect(() => {
    const updateWidth = () => {
      if (timelineRef.current) {
        setTimelineWidth(timelineRef.current.offsetWidth - 40);
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
    const x = e.clientX - rect.left - 20;
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

  // Handle timeline click
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

  // Touch event handlers
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
    <div style={{ userSelect: 'none' }}>
      {/* Time display */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '20px',
        fontSize: '14px',
        fontWeight: '600',
        color: 'var(--retro-black)'
      }}>
        <div style={{ display: 'flex', gap: '24px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: '700', letterSpacing: '0.5px' }}>START</span>
            <div style={{ color: 'var(--retro-black)', fontSize: '16px', fontWeight: '700' }}>{formatTime(startTime)}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: '700', letterSpacing: '0.5px' }}>END</span>
            <div style={{ color: 'var(--retro-black)', fontSize: '16px', fontWeight: '700' }}>{formatTime(endTime)}</div>
          </div>
        </div>
        
        <div style={{ textAlign: 'right' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: '700', letterSpacing: '0.5px' }}>DURATION</span>
          <div style={{ color: 'var(--retro-sage)', fontSize: '16px', fontWeight: '700' }}>
            {formatTime(endTime - startTime)}
          </div>
        </div>
      </div>

      {/* Timeline container */}
      <div 
        ref={timelineRef}
        onClick={handleTimelineClick}
        style={{
          position: 'relative',
          height: '80px',
          backgroundColor: 'var(--retro-light)',
          borderRadius: '12px',
          padding: '20px',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          border: '2px solid var(--retro-sage)',
          boxShadow: '0 4px 12px var(--dark-gray)'
        }}
      >
        {/* Timeline track */}
        <div style={{
          position: 'absolute',
          top: '35px',
          left: '20px',
          right: '20px',
          height: '10px',
          backgroundColor: 'var(--retro-cream)',
          borderRadius: '5px',
          overflow: 'hidden'
        }}>
          {/* Selection range */}
          <div style={{
            position: 'absolute',
            left: `${startPixel}px`,
            width: `${selectionWidth}px`,
            height: '100%',
            backgroundColor: 'var(--retro-black)',
            borderRadius: '5px',
            transition: isDragging ? 'none' : 'all 0.3s ease',
            boxShadow: '0 2px 8px var(--black)'
          }} />
        </div>

        {/* Hook markers */}
        {hooks.map((hook, index) => {
          const hookStart = timeToPixel(hook.start);
          const hookWidth = Math.max(timeToPixel(hook.end - hook.start), 3);
          
          return (
            <div
              key={index}
              onClick={(e) => {
                e.stopPropagation();
                handleHookClick(hook);
              }}
              style={{
                position: 'absolute',
                top: '20px',
                left: `${20 + hookStart}px`,
                width: `${hookWidth}px`,
                height: '40px',
                backgroundColor: 'var(--retro-sage)',
                borderRadius: '6px',
                cursor: 'pointer',
                border: '2px solid var(--retro-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
                fontWeight: '700',
                color: 'var(--retro-black)',
                transition: 'all 0.2s ease',
                zIndex: 10,
                boxShadow: '0 2px 8px var(--mint)'
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = 'scale(1.05)';
                e.target.style.backgroundColor = 'var(--mint-dark)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'scale(1)';
                e.target.style.backgroundColor = 'var(--retro-sage)';
              }}
              title={`${hook.title}\n${formatTime(hook.start)} - ${formatTime(hook.end)}\n${hook.reason || ''}`}
            >
              AI
            </div>
          );
        })}

        {/* Start handle */}
        <div
          onMouseDown={(e) => handleMouseDown(e, 'start')}
          onTouchStart={(e) => handleTouchStart(e, 'start')}
          style={{
            position: 'absolute',
            top: '15px',
            left: `${20 + startPixel - 6}px`,
            width: '12px',
            height: '50px',
            backgroundColor: 'var(--primary)',
            borderRadius: '6px',
            cursor: disabled ? 'not-allowed' : 'ew-resize',
            zIndex: 20,
            border: '2px solid var(--dark-gray)',
            boxShadow: '0 4px 12px var(--mint)',
            transition: isDragging && dragType === 'start' ? 'none' : 'all 0.2s ease',
            transform: isDragging && dragType === 'start' ? 'scale(1.1)' : 'scale(1)'
          }}
          onMouseEnter={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1)';
          }}
        />

        {/* End handle */}
        <div
          onMouseDown={(e) => handleMouseDown(e, 'end')}
          onTouchStart={(e) => handleTouchStart(e, 'end')}
          style={{
            position: 'absolute',
            top: '15px',
            left: `${20 + endPixel - 6}px`,
            width: '12px',
            height: '50px',
            backgroundColor: 'var(--retro-black)',
            borderRadius: '6px',
            cursor: disabled ? 'not-allowed' : 'ew-resize',
            zIndex: 20,
            border: '2px solid var(--dark-gray)',
            boxShadow: '0 4px 12px var(--mint-dark)',
            transition: isDragging && dragType === 'end' ? 'none' : 'all 0.2s ease',
            transform: isDragging && dragType === 'end' ? 'scale(1.1)' : 'scale(1)'
          }}
          onMouseEnter={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            if (!isDragging) e.target.style.transform = 'scale(1)';
          }}
        />

        {/* Time ruler */}
        <div style={{
          position: 'absolute',
          bottom: '8px',
          left: '20px',
          right: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '11px',
          color: 'var(--dark-gray)',
          fontWeight: '500'
        }}>
          <span>0:00</span>
          <span>{formatTime(videoDuration / 2)}</span>
          <span>{formatTime(videoDuration)}</span>
        </div>
      </div>

      {/* Instructions */}
      <div style={{
        fontSize: '13px',
        color: 'var(--dark-gray)',
        marginTop: '16px',
        textAlign: 'center',
        fontWeight: '500'
      }}>
        Drag the handles to set your trim points • Click AI markers to use suggested clips • Click anywhere to jump
      </div>
    </div>
  );
};

export default PremiumTimeline;