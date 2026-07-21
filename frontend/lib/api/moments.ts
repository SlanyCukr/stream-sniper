import { deleteJson, getJson, putJson } from './client'
import {
  requireArray,
  requireFiniteNumberField,
  requireRecord,
  requireStringField,
} from './contractGuards'

export type MomentReviewStatus = 'bookmarked' | 'rejected' | 'clipped' | 'published'
export interface MomentPhrase { phrase: string, count: number }
export interface MomentSampleMessage { text: string, count: number }

const REVIEW_STATUSES = new Set<MomentReviewStatus>([
  'bookmarked', 'rejected', 'clipped', 'published',
])

export const requireNullableMomentReviewStatus = (
  value: unknown,
  label: string,
): MomentReviewStatus | null => {
  if (value === null) return null
  if (typeof value === 'string' && REVIEW_STATUSES.has(value as MomentReviewStatus)) {
    return value as MomentReviewStatus
  }
  throw new TypeError(`${label} must be a supported review status or null`)
}

export const mapNullableMomentPhrases = (
  value: unknown,
  label: string,
): MomentPhrase[] | null => {
  if (value === null) return null
  return requireArray(value, label).map((item, index) => {
    const rowLabel = `${label}[${index}]`
    const row = requireRecord(item, rowLabel)
    return {
      phrase: requireStringField(row, 'phrase', rowLabel),
      count: requireFiniteNumberField(row, 'count', rowLabel),
    }
  })
}

export const mapNullableMomentSamples = (
  value: unknown,
  label: string,
): MomentSampleMessage[] | null => {
  if (value === null) return null
  return requireArray(value, label).map((item, index) => {
    const rowLabel = `${label}[${index}]`
    const row = requireRecord(item, rowLabel)
    return {
      text: requireStringField(row, 'text', rowLabel),
      count: requireFiniteNumberField(row, 'count', rowLabel),
    }
  })
}

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
  top_phrases: MomentPhrase[] | null
  sample_messages: MomentSampleMessage[] | null
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
  getJson('/moments', {
    status: request.status,
    creator_id: request.creatorId,
    limit: request.pageSize,
    offset: request.rowOffset,
  })

export const putMomentReview = (
  streamId: number,
  bucketMinute: string,
  status: MomentReviewStatus,
  metadata: { clipUrl?: string | null, note?: string | null } = {},
) => putJson(
  `/streams/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`,
  {
    status,
    clip_url: metadata.clipUrl ?? null,
    note: metadata.note ?? null,
  },
)

export const deleteMomentReview = (streamId: number, bucketMinute: string) =>
  deleteJson(`/streams/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`)
