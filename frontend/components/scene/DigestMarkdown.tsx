'use client'

import type { JSX, ReactNode } from 'react'

/**
 * Renderer for the scene digest's narrow markdown dialect — exactly the
 * constructs `build_digest` emits (## / ### headings, "-" and "1." list lines,
 * `**bold**` spans, bare https:// URLs) and nothing more. Deliberately not a
 * general markdown engine: unknown syntax degrades to plain text instead of
 * pulling in a renderer dependency for one page.
 */

const URL_RE = /https?:\/\/\S+/g
const BOLD_RE = /\*\*([^*]+)\*\*/g

/** Split one already-bold-free text run into text + anchor nodes. */
const linkify = (text: string, keyBase: string): ReactNode[] => {
    const nodes: ReactNode[] = []
    let cursor = 0
    for (const match of text.matchAll(URL_RE)) {
        const start = match.index
        if (start > cursor) nodes.push(text.slice(cursor, start))
        const href = match[0]
        nodes.push(
            <a key={`${keyBase}-a${start}`} href={href} target="_blank" rel="noreferrer">
                {href.replace(/^https?:\/\//, '')}
            </a>,
        )
        cursor = start + href.length
    }
    if (cursor < text.length) nodes.push(text.slice(cursor))
    return nodes
}

/** Render **bold** spans and bare URLs inside one line of digest text. */
export const renderInline = (text: string, keyBase: string): ReactNode[] => {
    const nodes: ReactNode[] = []
    let cursor = 0
    for (const match of text.matchAll(BOLD_RE)) {
        const start = match.index
        if (start > cursor) nodes.push(...linkify(text.slice(cursor, start), `${keyBase}-t${cursor}`))
        nodes.push(<strong key={`${keyBase}-b${start}`}>{match[1]}</strong>)
        cursor = start + match[0].length
    }
    if (cursor < text.length) nodes.push(...linkify(text.slice(cursor), `${keyBase}-t${cursor}`))
    return nodes
}

const LIST_ITEM_RE = /^(?:-|\d+\.)\s+/

interface DigestBlock {
    kind: 'h2' | 'h3' | 'list' | 'paragraph'
    lines: string[]
}

/** Group the digest's lines into heading / list / paragraph blocks. */
export const parseDigestBlocks = (markdown: string): DigestBlock[] => {
    const blocks: DigestBlock[] = []
    for (const rawLine of markdown.split('\n')) {
        const line = rawLine.trimEnd()
        if (!line.trim()) continue
        if (line.startsWith('## ') && !line.startsWith('### ')) {
            blocks.push({ kind: 'h2', lines: [line.slice(3)] })
        } else if (line.startsWith('### ')) {
            blocks.push({ kind: 'h3', lines: [line.slice(4)] })
        } else if (LIST_ITEM_RE.test(line)) {
            const previous = blocks[blocks.length - 1]
            const text = line.replace(LIST_ITEM_RE, '')
            if (previous?.kind === 'list') previous.lines.push(text)
            else blocks.push({ kind: 'list', lines: [text] })
        } else {
            blocks.push({ kind: 'paragraph', lines: [line] })
        }
    }
    return blocks
}

const DigestMarkdown = ({ markdown }: { markdown: string }): JSX.Element => (
    <div className="digest-body">
        {parseDigestBlocks(markdown).map((block, index) => {
            const key = `block-${index}`
            if (block.kind === 'h2') {
                return <h2 key={key} className="digest-h2">{renderInline(block.lines[0], key)}</h2>
            }
            if (block.kind === 'h3') {
                return <h3 key={key} className="digest-h3">{renderInline(block.lines[0], key)}</h3>
            }
            if (block.kind === 'list') {
                return (
                    <ul key={key} className="digest-list">
                        {block.lines.map((line, itemIndex) => (
                            <li key={`${key}-i${itemIndex}`}>{renderInline(line, `${key}-i${itemIndex}`)}</li>
                        ))}
                    </ul>
                )
            }
            return <p key={key} className="digest-p">{renderInline(block.lines[0], key)}</p>
        })}
    </div>
)

export default DigestMarkdown
