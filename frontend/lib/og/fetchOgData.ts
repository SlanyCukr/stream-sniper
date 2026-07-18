/**
 * Server-side, best-effort data fetch for social-unfurl (OpenGraph) images.
 *
 * OG images are rendered on the Node server by `next/og`, so they cannot reuse
 * the browser's relative `/api` proxy — they must call the backend directly at
 * `API_PROXY_TARGET`. Every request is time-boxed and wrapped so a slow or dead
 * backend degrades to a generic branded card instead of a 500: `fetchJson`
 * never throws, and each `map*Og` returns `null` when the payload lacks the one
 * field that makes the card meaningful.
 */
import { formatCompactNumber } from '@/utils/numberUtils'

const API_BASE = process.env.API_PROXY_TARGET ?? 'http://localhost:5002'
const OG_FETCH_TIMEOUT_MS = 2500
const MAX_TITLE = 64
const MAX_SUBTITLE = 80

export interface OgStat {
  label: string
  value: string
}

/**
 * The card's fully-resolved, presentation-ready shape. Every field is a string
 * the renderer drops straight into JSX — all formatting/truncation happens here
 * so `ogCard.tsx` stays a pure layout function.
 */
export interface OgCardData {
  kind: string
  title: string
  subtitle?: string
  stats: OgStat[]
  tags: string[]
}

/**
 * Branded fallback shown whenever a fetch fails or an id has no data, so an OG
 * route never throws. Exported for the Image components and the tests.
 */
export const GENERIC_OG_CARD: OgCardData = {
  kind: 'SCENE ANALYTICS',
  title: 'Stream Sniper',
  subtitle: 'Twitch stream & chat analytics for the scene',
  stats: [],
  tags: [],
}

const asRecord = (value: unknown): Record<string, unknown> | null => (
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
)

const asString = (value: unknown): string | null => (
  typeof value === 'string' && value.trim() !== '' ? value : null
)

const asFiniteNumber = (value: unknown): number | null => (
  typeof value === 'number' && Number.isFinite(value) ? value : null
)

/** Trim to a max length, appending an ellipsis when clipped. Pure — tested directly. */
export const truncate = (text: string, max: number): string => (
  text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`
)

/**
 * Best-effort JSON GET against the backend. Returns `null` on any failure
 * (timeout, network error, non-2xx status, invalid JSON) — never throws.
 */
async function fetchJson(path: string): Promise<unknown> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: AbortSignal.timeout(OG_FETCH_TIMEOUT_MS),
      headers: { accept: 'application/json' },
    })
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}

/**
 * Project a chatter passport payload onto card data. Returns `null` when the
 * nick — the card's headline — is absent.
 */
export function mapChatterOg(raw: unknown): OgCardData | null {
  const root = asRecord(raw)
  if (!root) return null

  const chatter = asRecord(root.chatter)
  const nick = asString(chatter?.nick)
  if (!nick) return null

  const totals = asRecord(root.totals)
  const stats: OgStat[] = []
  const messages = asFiniteNumber(totals?.messages)
  if (messages !== null) stats.push({ label: 'Messages', value: formatCompactNumber(messages) })
  const creators = asFiniteNumber(totals?.creators_visited)
  if (creators !== null) stats.push({ label: 'Channels', value: formatCompactNumber(creators) })

  const home = asRecord(root.home_channel)
  const homeName = asString(home?.creator_display_name)

  const archetypes = Array.isArray(root.archetypes) ? root.archetypes : []
  const tags = archetypes
    .map(entry => asString(asRecord(entry)?.label))
    .filter((label): label is string => label !== null)
    .slice(0, 3)

  return {
    kind: 'CHATTER PASSPORT',
    title: truncate(nick, MAX_TITLE),
    subtitle: homeName ? truncate(`Home channel · ${homeName}`, MAX_SUBTITLE) : undefined,
    stats,
    tags,
  }
}

/**
 * Project a stream detail payload onto card data. Returns `null` when the stream
 * has neither a title nor a creator name to show.
 */
export function mapStreamOg(raw: unknown): OgCardData | null {
  const root = asRecord(raw)
  if (!root) return null

  const info = asRecord(root.info)
  if (!info) return null

  const title = asString(info.title)
  const creator = asString(info.creator_display_name)
  if (!title && !creator) return null

  const stats: OgStat[] = []
  const messages = asFiniteNumber(info.message_count)
  if (messages !== null) stats.push({ label: 'Messages', value: formatCompactNumber(messages) })
  const chatters = Array.isArray(root.chatters) ? root.chatters.length : null
  if (chatters !== null) stats.push({ label: 'Chatters', value: formatCompactNumber(chatters) })

  return {
    kind: 'STREAM REPORT',
    title: truncate(title ?? creator ?? 'Untitled stream', MAX_TITLE),
    subtitle: title && creator ? truncate(`by ${creator}`, MAX_SUBTITLE) : undefined,
    stats,
    tags: [],
  }
}

/**
 * Project a creator summary payload onto card data. Returns `null` when the
 * creator has no display name or nick.
 */
export function mapCreatorOg(raw: unknown): OgCardData | null {
  const root = asRecord(raw)
  if (!root) return null

  const name = asString(root.display_name) ?? asString(root.nick)
  if (!name) return null

  const stats: OgStat[] = []
  const streams = asFiniteNumber(root.total_streams)
  if (streams !== null) stats.push({ label: 'Streams', value: formatCompactNumber(streams) })
  const messages = asFiniteNumber(root.total_messages)
  if (messages !== null) stats.push({ label: 'Messages', value: formatCompactNumber(messages) })
  const audience = asFiniteNumber(root.audience_size)
  if (audience !== null) stats.push({ label: 'Audience', value: formatCompactNumber(audience) })

  const regulars = asFiniteNumber(root.regulars)

  return {
    kind: 'CREATOR DOSSIER',
    title: truncate(name, MAX_TITLE),
    subtitle: regulars !== null ? `${formatCompactNumber(regulars)} regulars` : undefined,
    stats,
    tags: [],
  }
}

export const fetchChatterOgData = async (id: string): Promise<OgCardData | null> =>
  mapChatterOg(await fetchJson(`/chatters/${encodeURIComponent(id)}/passport`))

export const fetchStreamOgData = async (id: string): Promise<OgCardData | null> =>
  mapStreamOg(await fetchJson(`/streams/${encodeURIComponent(id)}`))

export const fetchCreatorOgData = async (id: string): Promise<OgCardData | null> =>
  mapCreatorOg(await fetchJson(`/creators/${encodeURIComponent(id)}/summary`))
