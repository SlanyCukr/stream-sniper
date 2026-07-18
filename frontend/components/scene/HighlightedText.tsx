'use client'

import { Fragment } from 'react'
import { splitHighlight } from './searchHighlight'

interface HighlightedTextProps {
  text: string
  query: string
}

/** Renders `text` with case-insensitive occurrences of `query` wrapped in a
 * night-ops highlight mark. Pure presentation over the `splitHighlight` helper. */
const HighlightedText = ({ text, query }: HighlightedTextProps) => (
  <>
    {splitHighlight(text, query).map((segment, index) => (
      <Fragment key={index}>
        {segment.match
          ? <mark className="search-hit-mark">{segment.text}</mark>
          : segment.text}
      </Fragment>
    ))}
  </>
)

export default HighlightedText
