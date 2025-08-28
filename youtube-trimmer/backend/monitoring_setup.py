"""
Production monitoring setup for video processing pipeline
Includes metrics collection, alerting, and performance tracking
"""
import logging
import time
import psutil
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import wraps
import asyncio

# Optional imports - will gracefully degrade if not available
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    import sentry_sdk
    from sentry_sdk import capture_exception, capture_message
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Metrics definitions (if Prometheus is available)
if PROMETHEUS_AVAILABLE:
    # Video processing metrics
    video_processing_duration = Histogram(
        'video_processing_duration_seconds',
        'Time spent processing videos',
        labelnames=['operation_type', 'format', 'has_subtitles', 'status']
    )
    
    video_processing_counter = Counter(
        'video_processing_total',
        'Total number of video processing requests',
        labelnames=['operation_type', 'status']
    )
    
    active_jobs_gauge = Gauge(
        'active_processing_jobs',
        'Number of currently active processing jobs',
        labelnames=['job_type']
    )
    
    system_resources_gauge = Gauge(
        'system_resource_usage',
        'System resource usage',
        labelnames=['resource_type']
    )
    
    timeout_counter = Counter(
        'processing_timeouts_total',
        'Total number of processing timeouts',
        labelnames=['operation_type', 'timeout_type']
    )

@dataclass
class ProcessingMetrics:
    """Container for processing metrics"""
    start_time: float
    operation_type: str
    format: str = "standard"
    has_subtitles: bool = False
    status: str = "started"
    job_id: str = ""
    user_id: int = 0

class PerformanceMonitor:
    """Monitor performance and collect metrics for video processing"""
    
    def __init__(self):
        self.active_jobs: Dict[str, ProcessingMetrics] = {}
        self.performance_history: List[Dict] = []
        self.alert_thresholds = {
            'avg_processing_time': 600,  # 10 minutes
            'timeout_rate': 0.1,  # 10% timeout rate
            'memory_usage': 0.85,  # 85% memory usage
            'cpu_usage': 0.90,  # 90% CPU usage
            'error_rate': 0.05  # 5% error rate
        }
        
        # Start system monitoring
        if PROMETHEUS_AVAILABLE:
            self._start_system_monitoring()
    
    def _start_system_monitoring(self):
        """Start background system resource monitoring"""
        async def monitor_system():
            while True:
                try:
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    system_resources_gauge.labels(resource_type='cpu').set(cpu_percent / 100)
                    
                    # Memory usage
                    memory = psutil.virtual_memory()
                    system_resources_gauge.labels(resource_type='memory').set(memory.percent / 100)
                    
                    # Disk usage
                    disk = psutil.disk_usage('/')
                    system_resources_gauge.labels(resource_type='disk').set(disk.percent / 100)
                    
                    await asyncio.sleep(30)  # Update every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error monitoring system resources: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        # Start the monitoring task
        asyncio.create_task(monitor_system())
    
    def start_processing(self, job_id: str, operation_type: str, **kwargs) -> ProcessingMetrics:
        """Start tracking a processing job"""
        metrics = ProcessingMetrics(
            start_time=time.time(),
            operation_type=operation_type,
            format=kwargs.get('format', 'standard'),
            has_subtitles=kwargs.get('has_subtitles', False),
            job_id=job_id,
            user_id=kwargs.get('user_id', 0)
        )
        
        self.active_jobs[job_id] = metrics
        
        # Update active jobs gauge
        if PROMETHEUS_AVAILABLE:
            active_jobs_gauge.labels(job_type=operation_type).inc()
        
        logger.info(f"Started tracking job {job_id}: {operation_type}")
        return metrics
    
    def finish_processing(self, job_id: str, status: str = "completed", error: Optional[Exception] = None):
        """Finish tracking a processing job"""
        if job_id not in self.active_jobs:
            logger.warning(f"Attempted to finish unknown job: {job_id}")
            return
        
        metrics = self.active_jobs[job_id]
        duration = time.time() - metrics.start_time
        metrics.status = status
        
        # Record metrics
        if PROMETHEUS_AVAILABLE:
            video_processing_duration.labels(
                operation_type=metrics.operation_type,
                format=metrics.format,
                has_subtitles=metrics.has_subtitles,
                status=status
            ).observe(duration)
            
            video_processing_counter.labels(
                operation_type=metrics.operation_type,
                status=status
            ).inc()
            
            active_jobs_gauge.labels(job_type=metrics.operation_type).dec()
        
        # Record performance history
        self.performance_history.append({
            'job_id': job_id,
            'operation_type': metrics.operation_type,
            'duration': duration,
            'status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'has_subtitles': metrics.has_subtitles,
            'format': metrics.format
        })
        
        # Keep only last 1000 records
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
        
        # Log slow operations
        if duration > 300 and status == "completed":  # 5+ minutes
            logger.warning(f"Slow processing job {job_id}: {duration:.1f}s for {metrics.operation_type}")
        
        # Send error to Sentry if available
        if error and SENTRY_AVAILABLE:
            capture_exception(error)
        
        # Clean up
        del self.active_jobs[job_id]
        
        logger.info(f"Finished tracking job {job_id}: {status} in {duration:.1f}s")
        
        # Check for alerts
        self._check_performance_alerts()
    
    def record_timeout(self, job_id: str, timeout_type: str = "processing"):
        """Record a timeout event"""
        if job_id in self.active_jobs:
            metrics = self.active_jobs[job_id]
            
            if PROMETHEUS_AVAILABLE:
                timeout_counter.labels(
                    operation_type=metrics.operation_type,
                    timeout_type=timeout_type
                ).inc()
            
            if SENTRY_AVAILABLE:
                capture_message(
                    f"Processing timeout: {job_id}",
                    level="warning",
                    extra={
                        'job_id': job_id,
                        'operation_type': metrics.operation_type,
                        'timeout_type': timeout_type,
                        'duration': time.time() - metrics.start_time
                    }
                )
        
        logger.warning(f"Timeout recorded for job {job_id}: {timeout_type}")
        self.finish_processing(job_id, status="timeout")
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        if not self.performance_history:
            return {'message': 'No performance data available'}
        
        completed_jobs = [j for j in self.performance_history if j['status'] == 'completed']
        failed_jobs = [j for j in self.performance_history if j['status'] in ['failed', 'timeout']]
        
        if completed_jobs:
            avg_duration = sum(j['duration'] for j in completed_jobs) / len(completed_jobs)
            max_duration = max(j['duration'] for j in completed_jobs)
            min_duration = min(j['duration'] for j in completed_jobs)
        else:
            avg_duration = max_duration = min_duration = 0
        
        total_jobs = len(self.performance_history)
        error_rate = len(failed_jobs) / total_jobs if total_jobs > 0 else 0
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': len(completed_jobs),
            'failed_jobs': len(failed_jobs),
            'active_jobs': len(self.active_jobs),
            'error_rate': error_rate,
            'avg_duration_seconds': avg_duration,
            'max_duration_seconds': max_duration,
            'min_duration_seconds': min_duration,
            'active_job_ids': list(self.active_jobs.keys())
        }
    
    def _check_performance_alerts(self):
        """Check if any performance thresholds are exceeded"""
        stats = self.get_performance_stats()
        alerts = []
        
        # Check average processing time
        if stats.get('avg_duration_seconds', 0) > self.alert_thresholds['avg_processing_time']:
            alerts.append(f"High average processing time: {stats['avg_duration_seconds']:.1f}s")
        
        # Check error rate
        if stats.get('error_rate', 0) > self.alert_thresholds['error_rate']:
            alerts.append(f"High error rate: {stats['error_rate']:.1%}")
        
        # Check system resources
        if PROMETHEUS_AVAILABLE:
            try:
                memory_usage = psutil.virtual_memory().percent / 100
                cpu_usage = psutil.cpu_percent() / 100
                
                if memory_usage > self.alert_thresholds['memory_usage']:
                    alerts.append(f"High memory usage: {memory_usage:.1%}")
                
                if cpu_usage > self.alert_thresholds['cpu_usage']:
                    alerts.append(f"High CPU usage: {cpu_usage:.1%}")
                    
            except Exception as e:
                logger.error(f"Error checking system resources: {e}")
        
        # Send alerts
        if alerts:
            alert_message = "Performance alerts: " + "; ".join(alerts)
            logger.warning(alert_message)
            
            if SENTRY_AVAILABLE:
                capture_message(alert_message, level="warning", extra=stats)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def monitor_processing(operation_type: str, **kwargs):
    """Decorator to automatically monitor processing functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **func_kwargs):
            job_id = func_kwargs.get('job_id') or kwargs.get('job_id', f"sync_{int(time.time())}")
            
            metrics = performance_monitor.start_processing(
                job_id=job_id,
                operation_type=operation_type,
                **kwargs
            )
            
            try:
                result = func(*args, **func_kwargs)
                performance_monitor.finish_processing(job_id, status="completed")
                return result
                
            except Exception as e:
                performance_monitor.finish_processing(job_id, status="failed", error=e)
                raise
                
        return wrapper
    return decorator

def setup_monitoring(prometheus_port: int = 8000, sentry_dsn: Optional[str] = None) -> Dict[str, bool]:
    """Setup monitoring services"""
    setup_status = {}
    
    # Setup Prometheus metrics endpoint
    if PROMETHEUS_AVAILABLE:
        try:
            start_http_server(prometheus_port)
            setup_status['prometheus'] = True
            logger.info(f"Prometheus metrics endpoint started on port {prometheus_port}")
        except Exception as e:
            setup_status['prometheus'] = False
            logger.error(f"Failed to start Prometheus endpoint: {e}")
    else:
        setup_status['prometheus'] = False
        logger.warning("Prometheus not available - install prometheus_client for metrics collection")
    
    # Setup Sentry error tracking
    if SENTRY_AVAILABLE and sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=0.1,  # Sample 10% of traces
                release=f"reely-backend@{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                environment="production"
            )
            setup_status['sentry'] = True
            logger.info("Sentry error tracking initialized")
        except Exception as e:
            setup_status['sentry'] = False
            logger.error(f"Failed to initialize Sentry: {e}")
    else:
        setup_status['sentry'] = False
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry not available - install sentry-sdk for error tracking")
    
    return setup_status

# Health check function
def get_health_status() -> Dict:
    """Get comprehensive health status"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'monitoring': {
            'prometheus_available': PROMETHEUS_AVAILABLE,
            'sentry_available': SENTRY_AVAILABLE,
        },
        'performance': performance_monitor.get_performance_stats()
    }
    
    # Check system resources
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_free_gb': disk.free / (1024**3)
        }
        
        # Mark as unhealthy if resources are critically low
        if memory.percent > 90 or disk.percent > 95:
            health['status'] = 'unhealthy'
            health['warnings'] = []
            
            if memory.percent > 90:
                health['warnings'].append(f"Low memory: {memory.percent:.1f}% used")
            if disk.percent > 95:
                health['warnings'].append(f"Low disk space: {disk.percent:.1f}% used")
                
    except Exception as e:
        health['system_error'] = str(e)
    
    return health

if __name__ == "__main__":
    # Example usage and testing
    setup_monitoring(prometheus_port=9090)
    
    # Simulate some processing jobs for testing
    import time
    
    @monitor_processing("test_processing", format="vertical", has_subtitles=True)
    def test_job(duration: float = 1.0):
        time.sleep(duration)
        return "completed"
    
    # Run test jobs
    for i in range(5):
        try:
            test_job(duration=0.5)
        except Exception as e:
            logger.error(f"Test job {i} failed: {e}")
    
    # Print stats
    stats = performance_monitor.get_performance_stats()
    print("Performance Stats:", stats)
    
    health = get_health_status()
    print("Health Status:", health)