import { api, buildQuery } from './client'

export interface TrackedStreamerListRequest {
  rowOffset?: number
  pageSize?: number
  isActive?: boolean | null
  processingEnabled?: boolean | null
}

export interface ProcessingJobListRequest {
  rowOffset?: number
  pageSize?: number
  status?: string
  trackedStreamerId?: number
}

export interface CreateTrackedStreamerRequest {
  twitch_username: string
  notes?: string | null
  is_active: boolean
  processing_enabled: boolean
}

export interface UpdateTrackedStreamerRequest {
  is_active?: boolean
  processing_enabled?: boolean
  notes?: string | null
}

export interface TrackedStreamerDto {
  id: number
  creator_id: number
  twitch_username: string
  display_name: string
  is_active: boolean
  last_stream_check: string | null
  last_processed_vod_id: number | null
  processing_enabled: boolean
  created_at: string
  updated_at: string
  created_by: number | null
  notes: string | null
  creator_display_name: string
  profile_image_url: string | null
  created_by_username: string | null
  total_streams_collected: number | null
  last_collected_stream_start: string | null
}

export interface TwitchProbeResultDto {
  is_live: boolean
  archive_vod_count: number
  last_vod_created_at: string | null
  checked_at: string
}

export interface TrackedStreamerListDto {
  streamers: TrackedStreamerDto[]
  total: number
  offset: number
  limit: number
}

export interface ProcessingJobDto {
  id: number
  tracked_streamer_id: number
  twitch_vod_id: number
  status: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  retry_count: number
  created_at: string
  updated_at: string
  twitch_username: string
  streamer_display_name: string
  stream_title: string | null
  stream_start: string | null
}

export interface ProcessingJobListDto {
  jobs: ProcessingJobDto[]
  total: number
  offset: number
  limit: number
}

export interface TrackingStatsDto {
  tracked_streamers: Record<string, number>
  processing_jobs: Record<string, number>
  system_status: {
    monitoring_active: boolean
    monitoring_degraded: boolean
    processing_queue_size: number
    failed_jobs: number
    scheduler_running: boolean
    active_jobs: number
    uptime_seconds: number | null
    heartbeat_state: string
  }
}

export type TwitchChannelSearchDto = Array<{
  login: string
  display_name: string
  profile_image_url: string
  is_live: boolean
}>

export const retrieveTwitchChannelSearch = (query: string, limit = 8) =>
  api.get<TwitchChannelSearchDto>(
    `/admin/tracking/twitch-search?${buildQuery({ q: query, limit })}`,
  )

export const retrieveTrackingStats = () =>
  api.get<TrackingStatsDto>('/admin/tracking/stats')

export const retrieveTrackedStreamers = (request: TrackedStreamerListRequest = {}) =>
  api.get<TrackedStreamerListDto>(`/admin/tracking/streamers?${buildQuery({
    offset: request.rowOffset,
    limit: request.pageSize,
    is_active: request.isActive,
    processing_enabled: request.processingEnabled,
  })}`)

export const createTrackedStreamer = (streamer: CreateTrackedStreamerRequest) =>
  api.post<TrackedStreamerDto>('/admin/tracking/streamers', streamer)

export const updateTrackedStreamer = (
  streamerId: number,
  changes: UpdateTrackedStreamerRequest,
) => api.put<TrackedStreamerDto>(`/admin/tracking/streamers/${streamerId}`, changes)

export const deleteTrackedStreamer = (streamerId: number) =>
  api.delete<void>(`/admin/tracking/streamers/${streamerId}`)

export const probeTwitchChannel = (streamerId: number) =>
  api.post<TwitchProbeResultDto>(`/admin/tracking/streamers/${streamerId}/probe`)

export const retrieveProcessingJobs = (request: ProcessingJobListRequest = {}) =>
  api.get<ProcessingJobListDto>(`/admin/tracking/jobs?${buildQuery({
    offset: request.rowOffset,
    limit: request.pageSize,
    status: request.status,
    tracked_streamer_id: request.trackedStreamerId,
  })}`)
