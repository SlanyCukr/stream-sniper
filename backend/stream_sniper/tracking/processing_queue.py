"""
Processing queue service for managing stream processing jobs.
"""

import asyncio
from typing import Any, Dict

from ..database.processing_jobs_table_gateway import (
    complete_processing_job_db,
    fail_processing_job_db,
    select_failed_jobs_for_retry_db,
    select_pending_jobs_db,
    start_processing_job_db,
    update_processing_job_db,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class ProcessingQueue:
    """
    Service for managing and processing stream processing jobs.
    """
    
    def __init__(self, max_concurrent_jobs: int = 3, max_retries: int = 3):
        if max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        self._running = False
        self._active_jobs: Dict[int, asyncio.Task] = {}
        
    async def start_processing(self):
        """Start the processing queue."""
        self._running = True
        self.logger.info("Starting processing queue...")
        
        try:
            while self._running:
                await self._process_queue()
                await asyncio.sleep(10)  # Check every 10 seconds
        except Exception as e:
            self.logger.error(f"Error in processing queue: {e}")
        finally:
            self.logger.info("Processing queue stopped")

    async def stop_processing(self):
        """Stop the processing queue."""
        self._running = False
        self.logger.info("Stopping processing queue...")
        
        # Cancel all active jobs
        for job_id, task in self._active_jobs.items():
            if not task.done():
                task.cancel()
                self.logger.info(f"Cancelled job {job_id}")
        
        # Wait for all jobs to complete
        if self._active_jobs:
            await asyncio.gather(*self._active_jobs.values(), return_exceptions=True)
        
        self._active_jobs.clear()

    async def _process_queue(self):
        """Process pending jobs in the queue."""
        try:
            # Check if we have capacity for more jobs
            if len(self._active_jobs) >= self.max_concurrent_jobs:
                return
            
            # Clean up completed jobs
            self._cleanup_completed_jobs()
            
            # Calculate how many jobs we can start
            available_slots = self.max_concurrent_jobs - len(self._active_jobs)
            
            if available_slots <= 0:
                return
            
            # Get pending jobs
            pending_jobs = select_pending_jobs_db(limit=available_slots)
            
            # Get failed jobs that can be retried
            if available_slots > len(pending_jobs):
                remaining_slots = available_slots - len(pending_jobs)
                retry_jobs = select_failed_jobs_for_retry_db(
                    max_retries=self.max_retries,
                    limit=remaining_slots
                )
                pending_jobs.extend(retry_jobs)
            
            # Start processing jobs
            for job_tuple in pending_jobs:
                if len(self._active_jobs) >= self.max_concurrent_jobs:
                    break
                
                job_id = job_tuple[0]
                task = asyncio.create_task(self._process_job(job_tuple))
                self._active_jobs[job_id] = task
                
                self.logger.info(f"Started processing job {job_id}")
                
        except Exception as e:
            self.logger.error(f"Error in _process_queue: {e}")

    def _cleanup_completed_jobs(self):
        """Remove completed jobs from active jobs tracking."""
        completed_jobs = []
        
        for job_id, task in self._active_jobs.items():
            if task.done():
                completed_jobs.append(job_id)
        
        for job_id in completed_jobs:
            del self._active_jobs[job_id]

    async def _process_job(self, job_tuple: tuple):
        """Process a single job."""
        job_id = job_tuple[0]
        twitch_stream_id = job_tuple[2]
        twitch_username = job_tuple[10]
        
        try:
            self.logger.info(f"Processing job {job_id} for stream {twitch_stream_id} by {twitch_username}")
            
            # Mark job as started
            if not start_processing_job_db(job_id):
                self.logger.error(f"Failed to mark job {job_id} as started")
                return
            
            # Import here to avoid circular imports
            from .stream_processor import StreamProcessor
            
            # Create stream processor
            processor = StreamProcessor()
            
            # Process the stream. Bound each queued job to a single VOD so one
            # job ingests one stream rather than the streamer's entire backlog.
            success = await processor.process_stream(
                twitch_username=twitch_username,
                twitch_stream_id=twitch_stream_id,
                job_id=job_id,
                max_streams=1
            )
            
            if success:
                # Mark job as completed
                if complete_processing_job_db(job_id):
                    self.logger.info(f"Job {job_id} completed successfully")
                else:
                    self.logger.error(f"Failed to mark job {job_id} as completed")
            else:
                # Mark job as failed
                error_message = "Stream processing failed"
                if fail_processing_job_db(job_id, error_message):
                    self.logger.error(f"Job {job_id} failed: {error_message}")
                else:
                    self.logger.error(f"Failed to mark job {job_id} as failed")
                    
        except asyncio.CancelledError:
            self.logger.info(f"Job {job_id} was cancelled")
            # Mark job as failed due to cancellation
            fail_processing_job_db(job_id, "Job was cancelled", increment_retry=False)
            raise
        except Exception as e:
            self.logger.error(f"Error processing job {job_id}: {e}")
            # Mark job as failed
            fail_processing_job_db(job_id, str(e))

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            'running': self._running,
            'active_jobs': len(self._active_jobs),
            'max_concurrent_jobs': self.max_concurrent_jobs,
            'max_retries': self.max_retries,
            'active_job_ids': list(self._active_jobs.keys())
        }

    async def cancel_job(self, job_id: int) -> bool:
        """Cancel a specific job."""
        if job_id in self._active_jobs:
            task = self._active_jobs[job_id]
            if not task.done():
                task.cancel()
                self.logger.info(f"Cancelled job {job_id}")
                return True
        return False

    async def retry_job(self, job_id: int) -> bool:
        """Retry a specific job."""
        try:
            # Reset job status to pending
            success = update_processing_job_db(
                job_id,
                status="pending",
                started_at=None,
                completed_at=None,
                error_message=None
            )
            
            if success:
                self.logger.info(f"Job {job_id} queued for retry")
                return True
            else:
                self.logger.error(f"Failed to queue job {job_id} for retry")
                return False
                
        except Exception as e:
            self.logger.error(f"Error retrying job {job_id}: {e}")
            return False