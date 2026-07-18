/**
 * Pure text-splitting helper for the scene search surface. Splits `text` into
 * ordered segments, flagging the ones that match `query` so the renderer can
 * wrap matches in a highlight span. Matching is case- AND accent-insensitive
 * (diacritics folded away), approximating the backend's `f_unaccent(lower())`
 * semantics so a search for "rekl" also highlights "řekl". `query` is treated
 * as plain text, not a regex.
 */

export interface HighlightSegment {
  text: string
  match: boolean
}

/**
 * Fold a string to lowercase base characters (NFD-decompose, strip combining
 * marks), keeping a map from each folded code unit back to the index of the
 * original code unit it came from so matches can be sliced out of the original.
 */
const foldWithMap = (value: string): { folded: string; map: number[] } => {
  let folded = ''
  const map: number[] = []
  for (let i = 0; i < value.length; i += 1) {
    const base = value[i].normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    for (const ch of base) {
      folded += ch
      map.push(i)
    }
  }
  return { folded, map }
}

const foldQuery = (value: string): string =>
  value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

/**
 * Split `text` into alternating non-match / match segments for `query`.
 * Empty or whitespace-only queries (or empty text) yield a single non-match
 * segment so callers can render unconditionally.
 */
export const splitHighlight = (text: string, query: string): HighlightSegment[] => {
  const trimmed = query.trim()
  if (!text || trimmed.length === 0) {
    return [{ text: text ?? '', match: false }]
  }

  const needle = foldQuery(trimmed)
  if (needle.length === 0) {
    return [{ text, match: false }]
  }
  const { folded, map } = foldWithMap(text)

  const segments: HighlightSegment[] = []
  let lastOriginalIndex = 0
  let searchFrom = 0

  while (searchFrom <= folded.length - needle.length) {
    const foundAt = folded.indexOf(needle, searchFrom)
    if (foundAt === -1) break
    const originalStart = map[foundAt]
    // End = one past the original code unit that produced the last folded char;
    // a match ending mid-expansion highlights the whole original character.
    const originalEnd = map[foundAt + needle.length - 1] + 1
    if (originalStart > lastOriginalIndex) {
      segments.push({ text: text.slice(lastOriginalIndex, originalStart), match: false })
    }
    segments.push({ text: text.slice(originalStart, originalEnd), match: true })
    lastOriginalIndex = originalEnd
    searchFrom = foundAt + needle.length
  }

  if (lastOriginalIndex < text.length) {
    segments.push({ text: text.slice(lastOriginalIndex), match: false })
  }

  return segments.length > 0 ? segments : [{ text, match: false }]
}
