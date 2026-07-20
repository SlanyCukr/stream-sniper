'use client'

import { useMemo, type JSX, type ReactNode } from 'react'

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

const BULLET_ITEM_RE = /^-\s+/
const ORDERED_ITEM_RE = /^\d+\.\s+/

interface DigestBlock {
    kind: 'h2' | 'h3' | 'list' | 'paragraph'
    lines: string[]
    /** For list blocks: true = numbered run (rendered <ol> to keep the ranks). */
    ordered?: boolean
}

/** Group the digest's lines into heading / list / paragraph blocks.

    Bullet ("- ") and numbered ("1. ") runs stay separate blocks so an ordered
    section (Most active chatters) keeps its rank numbers instead of collapsing
    into bullets. */
export const parseDigestBlocks = (markdown: string): DigestBlock[] => {
    const blocks: DigestBlock[] = []
    for (const rawLine of markdown.split('\n')) {
        const line = rawLine.trimEnd()
        if (!line.trim()) continue
        if (line.startsWith('## ') && !line.startsWith('### ')) {
            blocks.push({ kind: 'h2', lines: [line.slice(3)] })
        } else if (line.startsWith('### ')) {
            blocks.push({ kind: 'h3', lines: [line.slice(4)] })
        } else if (BULLET_ITEM_RE.test(line) || ORDERED_ITEM_RE.test(line)) {
            const ordered = ORDERED_ITEM_RE.test(line)
            const previous = blocks[blocks.length - 1]
            const text = line.replace(ordered ? ORDERED_ITEM_RE : BULLET_ITEM_RE, '')
            if (previous?.kind === 'list' && previous.ordered === ordered) previous.lines.push(text)
            else blocks.push({ kind: 'list', ordered, lines: [text] })
        } else {
            blocks.push({ kind: 'paragraph', lines: [line] })
        }
    }
    return blocks
}

const DigestMarkdown = ({ markdown }: { markdown: string }): JSX.Element => {
    // Parsing is regex-heavy; don't redo it when a parent re-renders (e.g. the
    // copy button's `copied` toggle) with the same markdown.
    const blocks = useMemo(() => parseDigestBlocks(markdown), [markdown])
    return (
        <div className="digest-body">
            {blocks.map((block, index) => {
                const key = `block-${index}`
                if (block.kind === 'h2') {
                    return <h2 key={key} className="digest-h2">{renderInline(block.lines[0], key)}</h2>
                }
                if (block.kind === 'h3') {
                    return <h3 key={key} className="digest-h3">{renderInline(block.lines[0], key)}</h3>
                }
                if (block.kind === 'list') {
                    const ListTag = block.ordered ? 'ol' : 'ul'
                    return (
                        <ListTag
                            key={key}
                            className={block.ordered ? 'digest-list digest-list-ordered' : 'digest-list'}
                        >
                            {block.lines.map((line, itemIndex) => (
                                <li key={`${key}-i${itemIndex}`}>{renderInline(line, `${key}-i${itemIndex}`)}</li>
                            ))}
                        </ListTag>
                    )
                }
                return <p key={key} className="digest-p">{renderInline(block.lines[0], key)}</p>
            })}
        </div>
    )
}

export default DigestMarkdown
