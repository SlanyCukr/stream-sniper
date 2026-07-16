import { api, buildQuery } from './client'

export type MomentReviewStatus = 'bookmarked' | 'rejected' | 'clipped' | 'published'

export interface MomentsQueueRequest {
  status?: 'pending' | MomentReviewStatus
  creatorId?: number
  pageSize?: number
  rowOffset?: number
}

export interface MomentQueueItemDto {
  stream_id: number
  title: string
  start: string
  twitch_id: string | null
  creator_display_name: string
  bucket_minute: string
  offset_seconds: number
  message_count: number
  baseline: number
  ratio: number | null
  unique_chatters: number
  sub_share: number | null
  emote_share: number | null
  top_phrases: Array<Record<string, unknown>> | null
  sample_messages: Array<Record<string, unknown>> | null
  status: MomentReviewStatus | null
  clip_url: string | null
  note: string | null
}

export interface MomentsQueueDto {
  items: MomentQueueItemDto[]
  total: number
  limit: number
  offset: number
}

export interface MomentReviewDto {
  status: MomentReviewStatus | null
  clip_url: string | null
  note: string | null
  updated_at: string | null
}

export const retrieveMomentsQueue = (request: MomentsQueueRequest = {}) =>
  api.get<MomentsQueueDto>(`/moments?${buildQuery({
    status: request.status,
    creator_id: request.creatorId,
    limit: request.pageSize,
    offset: request.rowOffset,
  })}`)

export const putMomentReview = (
  streamId: number,
  bucketMinute: string,
  status: MomentReviewStatus,
  metadata: { clipUrl?: string | null, note?: string | null } = {},
) => api.put<MomentReviewDto>(
  `/streams/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`,
  {
    status,
    clip_url: metadata.clipUrl ?? null,
    note: metadata.note ?? null,
  },
)

export const deleteMomentReview = (streamId: number, bucketMinute: string) =>
  api.delete<void>(`/streams/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`)
