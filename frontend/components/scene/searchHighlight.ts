/**
 * Pure text-splitting helper for the scene search surface. Splits `text` into
 * ordered segments, flagging the ones that match `query` case-insensitively so
 * the renderer can wrap matches in a highlight span. The match is literal
 * (accent-sensitive substring); `query` is treated as plain text, not a regex.
 */

export interface HighlightSegment {
  text: string
  match: boolean
}

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

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

  const pattern = new RegExp(`(${escapeRegExp(trimmed)})`, 'ig')
  const segments: HighlightSegment[] = []
  let lastIndex = 0
  let result: RegExpExecArray | null

  while ((result = pattern.exec(text)) !== null) {
    // Guard against zero-width matches looping forever.
    if (result.index === pattern.lastIndex) {
      pattern.lastIndex += 1
      continue
    }
    if (result.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, result.index), match: false })
    }
    segments.push({ text: result[0], match: true })
    lastIndex = result.index + result[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), match: false })
  }

  return segments.length > 0 ? segments : [{ text, match: false }]
}
