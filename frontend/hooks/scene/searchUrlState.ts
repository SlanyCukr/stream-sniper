/**
 * Pure mapping between the scene-search URL query string and the view's filter
 * state, so searches are shareable and the initial render can hydrate straight
 * from the address bar. `days === null` means "All time" (no `days` param sent).
 */

export const SEARCH_DAY_WINDOWS = [7, 30, 90, 365] as const

export interface SearchUrlState {
  q: string
  creatorId: number | null
  days: number | null
}

const parsePositiveInt = (value: string | null): number | null => {
  if (value === null) return null
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

/** Read the shareable filter state out of a URLSearchParams-like object. */
export const readSearchState = (
  params: Pick<URLSearchParams, 'get'>,
): SearchUrlState => {
  const days = parsePositiveInt(params.get('days'))
  return {
    q: (params.get('q') ?? '').slice(0, 200),
    creatorId: parsePositiveInt(params.get('creator_id')),
    days: days !== null && (SEARCH_DAY_WINDOWS as readonly number[]).includes(days) ? days : null,
  }
}

/**
 * Serialize filter state back to a query string (no leading `?`). Omits empty /
 * default values so the URL stays clean and "All time" produces no `days` key.
 */
export const buildSearchQueryString = (state: SearchUrlState): string => {
  const params = new URLSearchParams()
  const q = state.q.trim()
  if (q) params.set('q', q)
  if (state.creatorId != null) params.set('creator_id', String(state.creatorId))
  if (state.days != null) params.set('days', String(state.days))
  return params.toString()
}
