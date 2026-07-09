"""
Stream monitoring service for tracking Twitch streamers.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..collector.twitch_api import TwitchAPI
from ..database.processing_jobs_table_gateway import insert_processing_job_db, job_exists_db
from ..database.tracked_streamers_table_gateway import (
    select_active_tracked_streamers_db,
    update_stream_check_time_db,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StreamStatus:
    """Data class for stream status information."""
    twitch_username: str
    is_live: bool
    stream_id: Optional[int] = None
    title: Optional[str] = None
    started_at: Optional[datetime] = None
    viewer_count: Optional[int] = None
    last_checked: Optional[datetime] = None


class StreamMonitor:
    """
    Service for monitoring Twitch streams and detecting stream state changes.
    """
    
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self.check_interval = check_interval
        self.twitch_api = TwitchAPI()
        self.logger = get_logger(__name__)
        self._running = False
        self._last_stream_states: Dict[str, bool] = {}
        
    async def initialize(self):
        """Initialize the Twitch API connection (idempotent across restarts)."""
        try:
            await self.twitch_api.ensure_initialized()
            self.logger.info("Stream monitor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize stream monitor: {e}")
            raise

    async def start_monitoring(self):
        """Start the stream monitoring loop."""
        self._running = True
        self.logger.info("Starting stream monitoring...")
        
        try:
            while self._running:
                await self._check_all_streams()
                await asyncio.sleep(self.check_interval)
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
        finally:
            self.logger.info("Stream monitoring stopped")

    async def stop_monitoring(self):
        """Stop the stream monitoring loop."""
        self._running = False
        self.logger.info("Stopping stream monitoring...")

    async def _check_all_streams(self):
        """Check all tracked streamers for stream status changes."""
        try:
            # Get all active tracked streamers
            tracked_streamers = select_active_tracked_streamers_db()
            
            if not tracked_streamers:
                self.logger.debug("No active tracked streamers found")
                return
            
            self.logger.info(f"Checking {len(tracked_streamers)} tracked streamers")
            
            # Check each streamer
            for streamer in tracked_streamers:
                try:
                    await self._check_single_stream(streamer)
                except Exception as e:
                    self.logger.error(f"Error checking stream for {streamer[2]}: {e}")
                
                # Small delay between checks to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in _check_all_streams: {e}")

    async def _check_single_stream(self, streamer_data: tuple):
        """Check a single streamer for stream status changes."""
        try:
            # Extract streamer data
            (ts_id, creator_id, twitch_username, display_name, is_active,
             last_stream_check, last_processed_stream_id, processing_enabled,
             created_at, updated_at, created_by, notes,
             creator_display_name, profile_image_url, created_by_username) = streamer_data
            
            # Get current stream status
            stream_status = await self._get_stream_status(twitch_username)
            
            # Update last check time
            update_stream_check_time_db(ts_id, datetime.now())
            
            # Check if stream state changed
            previous_state = self._last_stream_states.get(twitch_username, False)
            current_state = stream_status.is_live
            
            self.logger.debug(
                f"Stream check for {twitch_username}: "
                f"Previous={previous_state}, Current={current_state}"
            )
            
            # Update state tracking
            self._last_stream_states[twitch_username] = current_state
            
            # If stream just ended, queue it for processing
            if previous_state and not current_state:
                self.logger.info(f"Stream ended for {twitch_username}, queuing for processing")
                await self._queue_stream_for_processing(ts_id, twitch_username)
                
            # If stream just started, log it
            elif not previous_state and current_state:
                self.logger.info(f"Stream started for {twitch_username}")
                
        except Exception as e:
            self.logger.error(f"Error checking single stream for {streamer_data[2]}: {e}")

    async def _get_stream_status(self, twitch_username: str) -> StreamStatus:
        """Get current stream status for a Twitch username."""
        try:
            # Set the streamer nickname for the API
            self.twitch_api.set_streamer_nickname(twitch_username)
            
            # Get stream info
            stream_info = await self.twitch_api.get_stream_info_async()
            
            if stream_info:
                return StreamStatus(
                    twitch_username=twitch_username,
                    is_live=True,
                    stream_id=int(stream_info.id),
                    title=stream_info.title,
                    started_at=stream_info.started_at,
                    viewer_count=stream_info.viewer_count,
                    last_checked=datetime.now()
                )
            else:
                return StreamStatus(
                    twitch_username=twitch_username,
                    is_live=False,
                    last_checked=datetime.now()
                )
                
        except Exception as e:
            self.logger.error(f"Error getting stream status for {twitch_username}: {e}")
            return StreamStatus(
                twitch_username=twitch_username,
                is_live=False,
                last_checked=datetime.now()
            )

    async def _queue_stream_for_processing(self, tracked_streamer_id: int, twitch_username: str):
        """Queue a stream for processing when it ends."""
        try:
            # Get the most recent stream for this user
            recent_streams = await self._get_recent_streams(twitch_username)
            
            if not recent_streams:
                self.logger.warning(f"No recent streams found for {twitch_username}")
                return
            
            # Get the most recent stream
            latest_stream = recent_streams[0]
            twitch_stream_id = int(latest_stream.id)
            
            # Check if we already have a processing job for this stream
            if job_exists_db(tracked_streamer_id, twitch_stream_id):
                self.logger.debug(f"Processing job already exists for stream {twitch_stream_id}")
                return
            
            # Create processing job
            job_id = insert_processing_job_db(tracked_streamer_id, twitch_stream_id)
            
            if job_id:
                self.logger.info(
                    f"Created processing job {job_id} for stream {twitch_stream_id} "
                    f"by {twitch_username}"
                )
            else:
                self.logger.error(f"Failed to create processing job for stream {twitch_stream_id}")
                
        except Exception as e:
            self.logger.error(f"Error queuing stream for processing: {e}")

    async def _get_recent_streams(self, twitch_username: str, limit: int = 5) -> List[Any]:
        """Get recent streams for a Twitch username."""
        try:
            # Set the streamer nickname for the API
            self.twitch_api.set_streamer_nickname(twitch_username)
            
            # Get available video IDs (recent streams)
            videos = await self.twitch_api.get_available_video_ids_async()
            
            # Return the most recent videos (limited)
            return videos[:limit] if videos else []
            
        except Exception as e:
            self.logger.error(f"Error getting recent streams for {twitch_username}: {e}")
            return []

    async def check_streamer_now(self, twitch_username: str) -> StreamStatus:
        """Check a specific streamer's current status (for manual checks)."""
        try:
            return await self._get_stream_status(twitch_username)
        except Exception as e:
            self.logger.error(f"Error checking streamer {twitch_username}: {e}")
            return StreamStatus(
                twitch_username=twitch_username,
                is_live=False,
                last_checked=datetime.now()
            )

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'running': self._running,
            'check_interval': self.check_interval,
            'tracked_streamers_count': len(self._last_stream_states),
            'last_stream_states': self._last_stream_states.copy()
        }