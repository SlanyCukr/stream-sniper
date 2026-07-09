# Stream Sniper - Automated Tracking System

## Overview

The Stream Sniper Automated Tracking System enables administrators to monitor Twitch streamers and automatically process their chat data when streams end. This system eliminates the need for manual data collection by continuously monitoring stream status and triggering processing jobs automatically.

## Features

### Core Functionality
- **Automated Stream Monitoring**: Continuously monitors tracked streamers for stream state changes
- **Automatic Processing**: Triggers chat data processing when streams end
- **Job Management**: Queues and manages processing jobs with retry capabilities
- **Admin Interface**: Complete web-based administration for managing tracked streamers
- **Service Control**: Start, stop, and restart the tracking service through the admin interface

### Technical Features
- **Concurrent Processing**: Configurable concurrent job processing
- **Retry Logic**: Automatic retry of failed processing jobs
- **Real-time Status**: Live monitoring of system status and job progress
- **Database Integration**: Normalized database schema for tracking data
- **API Endpoints**: RESTful API for all tracking operations

## Architecture

### Backend Components

#### 1. Stream Monitor (`stream_monitor.py`)
- Polls Twitch API every 5 minutes (configurable)
- Detects stream state changes (online/offline)
- Creates processing jobs when streams end
- Tracks last stream check times

#### 2. Processing Queue (`processing_queue.py`)
- Manages concurrent processing jobs
- Handles job scheduling and execution
- Implements retry logic for failed jobs
- Supports job cancellation and manual retry

#### 3. Stream Processor (`stream_processor.py`)
- Processes stream chat data using existing `TwitchCollectorFacade`
- Updates tracking information after successful processing
- Handles processing errors and timeouts

#### 4. Tracking Scheduler (`scheduler.py`)
- Coordinates all tracking services
- Manages service lifecycle (start/stop/restart)
- Provides system status and health monitoring
- Handles graceful shutdown

### Frontend Components

#### 1. Tracking Dashboard (`TrackingDashboard.jsx`)
- Overview of tracking system status
- Real-time metrics and statistics
- Service control buttons
- System health indicators

#### 2. Streamer Management (`StreamerTracking.jsx`)
- Add/remove streamers from tracking
- Configure streamer settings
- View tracking status and history
- Enable/disable processing for specific streamers

#### 3. Processing Jobs (`ProcessingJobs.jsx`)
- View all processing jobs with filtering
- Monitor job status and progress
- Cancel or retry failed jobs
- View job details and error messages

## Database Schema

### Tracked Streamers Table
```sql
CREATE TABLE stream_sniper.tracked_streamers (
    id SERIAL PRIMARY KEY,
    creator_id INT NOT NULL REFERENCES stream_sniper.creator(id),
    twitch_username VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_stream_check TIMESTAMP NULL,
    last_processed_stream_id BIGINT NULL,
    processing_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES stream_sniper.users(id),
    notes TEXT
);
```

### Processing Jobs Table
```sql
CREATE TABLE stream_sniper.processing_jobs (
    id SERIAL PRIMARY KEY,
    tracked_streamer_id INT NOT NULL REFERENCES stream_sniper.tracked_streamers(id),
    twitch_stream_id BIGINT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    error_message TEXT NULL,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Streamer Management
- `GET /admin/tracking/streamers` - List tracked streamers
- `POST /admin/tracking/streamers` - Add new streamer
- `GET /admin/tracking/streamers/{id}` - Get streamer details
- `PUT /admin/tracking/streamers/{id}` - Update streamer settings
- `DELETE /admin/tracking/streamers/{id}` - Remove streamer

### Processing Jobs
- `GET /admin/tracking/jobs` - List processing jobs
- `POST /admin/tracking/jobs/{id}/cancel` - Cancel job
- `POST /admin/tracking/jobs/{id}/retry` - Retry failed job

### Service Management
- `GET /admin/tracking/service/status` - Get service status
- `POST /admin/tracking/service/start` - Start tracking service
- `POST /admin/tracking/service/stop` - Stop tracking service
- `POST /admin/tracking/service/restart` - Restart tracking service

### Statistics
- `GET /admin/tracking/stats` - Get tracking statistics

## Installation & Setup

### 1. Database Setup
Run the updated database schema:
```bash
psql -U postgres -d stream_sniper -f backend/stream_sniper/database/create_table.sql
```

### 2. Install Dependencies
The tracking system uses the existing dependencies. No additional packages required.

### 3. Environment Configuration
Ensure your `.env` file contains the required database and API configuration:
```
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=stream_sniper
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Usage

### Starting the System

#### Development Mode
```bash
# Start the API server
docker-compose up api

# Start the tracking service (separate terminal)
docker-compose exec api python -m stream_sniper.tracking_service

# Or use the CLI command
stream-sniper-tracking
```

#### Production Mode
```bash
# Start all services
docker-compose up -d

# The tracking service can be managed through the admin interface
# or started as a separate service
```

### Admin Interface

1. **Access Admin Panel**: Navigate to `/admin/tracking` in your browser
2. **Add Streamers**: Use the "Add Streamer" button to add new streamers to track
3. **Monitor Status**: View real-time tracking status and statistics
4. **Manage Jobs**: View and manage processing jobs in the jobs section
5. **Service Control**: Start/stop/restart the tracking service as needed

### CLI Commands

```bash
# Start tracking service
stream-sniper-tracking

# Process individual streamer (existing functionality)
stream-sniper username

# Start API server
stream-sniper-api
```

## Configuration

### Tracking Settings
- **Monitor Interval**: How often to check stream status (default: 5 minutes)
- **Max Concurrent Jobs**: Maximum simultaneous processing jobs (default: 3)
- **Max Retries**: Maximum retry attempts for failed jobs (default: 3)

### Customization
Configure these settings in the `TrackingScheduler` initialization:
```python
scheduler = TrackingScheduler(
    monitor_interval=300,  # 5 minutes
    max_concurrent_jobs=3,
    max_retries=3
)
```

## Monitoring & Troubleshooting

### Logs
- **API Logs**: Available through `docker-compose logs api`
- **Service Logs**: Available through `docker-compose logs tracking`
- **Database Logs**: Check PostgreSQL logs for database issues

### Health Checks
- **Service Status**: `/admin/tracking/service/status`
- **System Health**: `/admin/tracking/stats`
- **API Health**: `/health`

### Common Issues

1. **Service Not Starting**: Check database connectivity and credentials
2. **Jobs Failing**: Review job error messages in the processing jobs view
3. **Streamers Not Monitored**: Verify streamer exists on Twitch and is active
4. **Database Connection**: Ensure PostgreSQL is running and accessible

## Security Considerations

- All tracking endpoints require admin authentication
- Service management operations are restricted to admin users
- Database operations use parameterized queries to prevent SQL injection
- API rate limiting is enforced for all endpoints

## Performance Optimization

- **Concurrent Processing**: Configure based on system resources
- **Monitoring Interval**: Balance between responsiveness and API limits
- **Database Indexing**: Indexes on frequently queried fields
- **Caching**: In-process TTL caching for frequently accessed data

## Scalability

The system is designed to handle:
- **Streamers**: Hundreds of tracked streamers
- **Processing Jobs**: Thousands of concurrent jobs
- **Database**: Millions of processed messages
- **API Requests**: High-frequency admin operations

## Future Enhancements

- Real-time stream notifications
- Advanced filtering and search capabilities
- Export functionality for tracking data
- Integration with external notification systems
- Advanced analytics and reporting
- Mobile-friendly admin interface

## Contributing

When contributing to the tracking system:
1. Follow existing code patterns and structure
2. Add appropriate tests for new functionality
3. Update documentation for API changes
4. Ensure proper error handling and logging
5. Test with various stream scenarios

## License

This tracking system is part of the Stream Sniper project and follows the same MIT license.