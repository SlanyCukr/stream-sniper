"""
Stream processor service for automated chat data processing.
"""

import asyncio
from typing import Any, Dict, Optional

from ..collector.twitch_collector_facade import TwitchCollectorFacade
from ..database.tracked_streamers_table_gateway import update_last_processed_stream_db
from ..logging_config import get_logger

logger = get_logger(__name__)


class StreamProcessor:
    """
    Service for processing stream chat data automatically.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def process_stream(
        self,
        twitch_username: str,
        twitch_stream_id: int,
        job_id: Optional[int] = None,
        max_streams: Optional[int] = None
    ) -> bool:
        """
        Process a stream's chat data.

        Args:
            twitch_username: Twitch username of the streamer
            twitch_stream_id: Twitch stream ID to process
            job_id: Optional job ID for tracking
            max_streams: Optional cap on how many VODs the collector processes in
                this run (None = all un-collected VODs). Queued jobs pass 1 so a
                single job ingests one VOD rather than the whole backlog.

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting stream processing for {twitch_username}, stream {twitch_stream_id}")

            # Create collector facade
            collector = TwitchCollectorFacade(twitch_username)

            # Run processing in a separate thread to avoid blocking
            # Since TwitchCollectorFacade is not async, we need to run it in an executor
            loop = asyncio.get_running_loop()

            def run_collector():
                try:
                    # Process the stream
                    collector.start_processing(max_streams=max_streams)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in collector processing: {e}")
                    return False
            
            # Run the collector in a thread pool
            success = await loop.run_in_executor(None, run_collector)
            
            if success:
                self.logger.info(f"Successfully processed stream {twitch_stream_id} for {twitch_username}")
                return True
            else:
                self.logger.error(f"Failed to process stream {twitch_stream_id} for {twitch_username}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing stream {twitch_stream_id} for {twitch_username}: {e}")
            return False
    
    async def process_stream_with_tracking(
        self,
        tracked_streamer_id: int,
        twitch_username: str,
        twitch_stream_id: int,
        job_id: Optional[int] = None
    ) -> bool:
        """
        Process a stream and update tracking information.
        
        Args:
            tracked_streamer_id: ID of the tracked streamer
            twitch_username: Twitch username of the streamer
            twitch_stream_id: Twitch stream ID to process
            job_id: Optional job ID for tracking
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Process the stream
            success = await self.process_stream(
                twitch_username=twitch_username,
                twitch_stream_id=twitch_stream_id,
                job_id=job_id
            )
            
            if success:
                # Update last processed stream ID
                update_last_processed_stream_db(tracked_streamer_id, twitch_stream_id)
                self.logger.info(f"Updated last processed stream for tracked streamer {tracked_streamer_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing stream with tracking: {e}")
            return False
    
    def get_processor_status(self) -> Dict[str, Any]:
        """Get processor status information."""
        return {
            'processor_active': True,
            'processor_type': 'TwitchCollectorFacade'
        }