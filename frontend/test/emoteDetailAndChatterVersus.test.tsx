import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const chatterApi = vi.hoisted(() => ({
    retrieveChatterHeadToHead: vi.fn(),
    retrieveChatterSearch: vi.fn(),
}))
const sceneApi = vi.hoisted(() => ({ retrieveEmoteDetail: vi.fn() }))

vi.mock('@/lib/api/chatter', () => chatterApi)
vi.mock('@/lib/api/scene', () => sceneApi)
vi.mock('@/components/common/search/AsyncSearchSelect', () => ({
    default: (props: {
        value: { value: number } | null
        onChange: (value: unknown) => void
        'aria-label'?: string
    }) => (
        <select
            aria-label={props['aria-label']}
            value={props.value?.value ?? ''}
            onChange={event => {
                const value = Number(event.target.value)
                props.onChange(value ? { value, label: value === 100 ? 'alpha' : 'beta', isBot: false } : null)
            }}
        >
            <option value="">Choose chatter</option>
            <option value="100">alpha</option>
            <option value="200">beta</option>
        </select>
    ),
}))

import { mapEmoteDetail } from '@/hooks/scene/useEmoteDetailQuery'
import { mapChatterHeadToHead } from '@/hooks/chatter/useChatterVersusQuery'
import { parseDigestBlocks, renderInline } from '@/components/scene/DigestMarkdown'
import ChatterVersus from '@/views/community/ChatterVersus'
import EmoteDetail from '@/views/scene/EmoteDetail'
import { navigationState, router } from './mocks/navigation'
import { renderWithQueryClient } from './render'

const emoteDetailPayload = {
    meta: { emote_id: 7, name: 'agrPls', source: 'bttv', provider_id: 'abc', first_seen: '2024-01-01T00:00:00' },
    totals: { usage: 400, chatter_reach: 70, stream_count: 3, creator_count: 2, last_used: '2026-07-18T19:00:00' },
    top_creators: [
        {
            creator_id: 1, nick: 'agraelus', display_name: 'Agraelus',
            usage: 350, chatter_reach: 60, stream_count: 2,
        },
    ],
    weekly_usage: [{ week_start: '2026-07-13', usage: 250 }],
    recent_streams: [
        {
            stream_id: 12, title: 'S3', start: '2026-07-18T17:00:00',
            creator_id: 2, creator_nick: 'claina', creator_display_name: 'Claina',
            usage: 50, chatter_count: 10,
        },
    ],
}

describe('mapEmoteDetail', () => {
    it('maps the full wire payload to camelCase', () => {
        const detail = mapEmoteDetail(emoteDetailPayload)
        expect(detail.meta.emoteId).toBe(7)
        expect(detail.totals.chatterReach).toBe(70)
        expect(detail.topCreators[0].displayName).toBe('Agraelus')
        expect(detail.weeklyUsage[0].weekStart).toBe('2026-07-13')
        expect(detail.recentStreams[0].creatorDisplayName).toBe('Claina')
    })

    it('accepts an unused emote (zero totals, empty sections)', () => {
        const detail = mapEmoteDetail({
            ...emoteDetailPayload,
            totals: { usage: 0, chatter_reach: 0, stream_count: 0, creator_count: 0, last_used: null },
            top_creators: [],
            weekly_usage: [],
            recent_streams: [],
        })
        expect(detail.totals.usage).toBe(0)
        expect(detail.totals.lastUsed).toBeNull()
        expect(detail.topCreators).toEqual([])
    })

    it('rejects a payload missing a totals field', () => {
        const brokenTotals: Record<string, unknown> = { ...emoteDetailPayload.totals }
        delete brokenTotals.chatter_reach
        expect(() => mapEmoteDetail({ ...emoteDetailPayload, totals: brokenTotals }))
            .toThrow(/chatter_reach/)
    })
})

const versusPayload = {
    a: {
        chatter_id: 100, nick: 'alpha', is_bot: false,
        messages: 1000, streams_attended: 15, creators_visited: 2,
        first_seen: '2024-01-01T20:00:00', last_seen: '2026-06-01T13:37:00',
        home_channel: {
            creator_id: 5, creator_nick: 'homie', creator_display_name: 'Homie',
            messages: 900, share: 0.9,
        },
        archetypes: [{ key: 'loyalist', label: 'Loyalist', description: 'Home share above 80%' }],
    },
    b: {
        chatter_id: 200, nick: 'beta', is_bot: null,
        messages: 0, streams_attended: 0, creators_visited: 0,
        first_seen: null, last_seen: null,
        home_channel: null,
        archetypes: [],
    },
    shared_streams: 6,
    shared_creators: 2,
}

describe('interactive emote and chatter views', () => {
    beforeEach(() => vi.clearAllMocks())

    it('gates chatter comparison, rejects identical picks, syncs the URL, and renders a valid pair', async () => {
        navigationState.pathname = '/versus/chatters'
        chatterApi.retrieveChatterHeadToHead.mockResolvedValue(versusPayload)
        renderWithQueryClient(<ChatterVersus />)

        expect(screen.getByText('Pick two chatters')).toBeInTheDocument()
        expect(chatterApi.retrieveChatterHeadToHead).not.toHaveBeenCalled()

        fireEvent.change(screen.getByLabelText('First chatter'), { target: { value: '100' } })
        expect(router.replace).toHaveBeenLastCalledWith('/versus/chatters?a=100', { scroll: false })
        expect(chatterApi.retrieveChatterHeadToHead).not.toHaveBeenCalled()

        fireEvent.change(screen.getByLabelText('Second chatter'), { target: { value: '100' } })
        expect(screen.getByText('Same chatter on both sides')).toBeInTheDocument()
        expect(chatterApi.retrieveChatterHeadToHead).not.toHaveBeenCalled()

        fireEvent.change(screen.getByLabelText('Second chatter'), { target: { value: '200' } })
        await waitFor(() => expect(chatterApi.retrieveChatterHeadToHead).toHaveBeenCalledWith(100, 200))
        expect(await screen.findByRole('link', { name: 'alpha' })).toHaveAttribute('href', '/chatter/100')
        expect(screen.getByRole('link', { name: 'beta' })).toHaveAttribute('href', '/chatter/200')
        expect(screen.getByText('Shared streams').nextElementSibling).toHaveTextContent('6')
        expect(router.replace).toHaveBeenLastCalledWith('/versus/chatters?a=100&b=200', { scroll: false })
    })

    it('renders populated emote sections from the real query boundary', async () => {
        sceneApi.retrieveEmoteDetail.mockResolvedValue(emoteDetailPayload)
        renderWithQueryClient(<EmoteDetail emoteId={7} />)

        expect(await screen.findByRole('heading', { name: /agrPls/ })).toBeInTheDocument()
        expect(sceneApi.retrieveEmoteDetail).toHaveBeenCalledWith(7)
        expect(screen.getByRole('link', { name: 'Agraelus' })).toHaveAttribute('href', '/creator/1')
        expect(screen.getByRole('link', { name: 'S3' })).toHaveAttribute('href', '/stream/12')
        expect(screen.getByRole('list', { name: 'Usage per week' })).toBeInTheDocument()
    })

    it('renders every intentional empty emote section explicitly', async () => {
        sceneApi.retrieveEmoteDetail.mockResolvedValue({
            ...emoteDetailPayload,
            totals: { usage: 0, chatter_reach: 0, stream_count: 0, creator_count: 0, last_used: null },
            top_creators: [],
            weekly_usage: [],
            recent_streams: [],
        })
        renderWithQueryClient(<EmoteDetail emoteId={7} />)

        expect(await screen.findByText('Not used in any tracked channel yet.')).toBeInTheDocument()
        expect(screen.getByText('No usage in the trailing 12 weeks.')).toBeInTheDocument()
        expect(screen.getByText('No streams recorded for this emote yet.')).toBeInTheDocument()
    })
})

describe('mapChatterHeadToHead', () => {
    it('maps both sides including nested home channel and archetypes', () => {
        const data = mapChatterHeadToHead(versusPayload)
        expect(data.a.homeChannel?.creatorDisplayName).toBe('Homie')
        expect(data.a.archetypes[0].key).toBe('loyalist')
        expect(data.a.isBot).toBe(false)
        expect(data.sharedStreams).toBe(6)
    })

    it('accepts a zero side with null home channel (never-crossed-paths contract)', () => {
        const data = mapChatterHeadToHead(versusPayload)
        expect(data.b.homeChannel).toBeNull()
        expect(data.b.isBot).toBeNull()
        expect(data.b.messages).toBe(0)
        expect(data.b.firstSeen).toBeNull()
    })

    it('rejects a side missing shared counters', () => {
        const broken: Record<string, unknown> = { ...versusPayload }
        delete broken.shared_streams
        expect(() => mapChatterHeadToHead(broken)).toThrow(/shared_streams/)
    })
})

describe('digest markdown parsing', () => {
    it('groups headings, list runs, and paragraphs', () => {
        const markdown = [
            '## Stream Sniper · 7-day scene pulse',
            '- **Agraelus finished a stream** — 17,739 messages',
            '- **A copypasta reached Claina** — catJAM',
            '',
            '### Biggest moments',
            '- **Agraelus** — spike → https://stream-sniper.slanycukr.com/stream/99',
            'No notable captured events in this window.',
        ].join('\n')

        const blocks = parseDigestBlocks(markdown)
        expect(blocks.map(block => block.kind)).toEqual(['h2', 'list', 'h3', 'list', 'paragraph'])
        expect(blocks[1].lines).toHaveLength(2)
        expect(blocks[1].lines[0]).toContain('**Agraelus finished a stream**')
    })

    it('renders bold spans and bare URLs as nodes', () => {
        const nodes = renderInline('**Agraelus** — spike → https://example.com/stream/99', 'k')
        // strong element + anchor element among the nodes
        const hasStrong = nodes.some(node => typeof node === 'object' && node !== null && 'type' in node && node.type === 'strong')
        const hasAnchor = nodes.some(node => typeof node === 'object' && node !== null && 'type' in node && node.type === 'a')
        expect(hasStrong).toBe(true)
        expect(hasAnchor).toBe(true)
    })

    it('parses numbered chatter lines as an ORDERED list (ranks preserved)', () => {
        const blocks = parseDigestBlocks('### Most active chatters\n1. **rybicka** — 4200 msgs\n2. **karel** — 900 msgs')
        expect(blocks[1].kind).toBe('list')
        expect(blocks[1].ordered).toBe(true)
        expect(blocks[1].lines).toEqual(['**rybicka** — 4200 msgs', '**karel** — 900 msgs'])
    })

    it('keeps bullet and numbered runs as separate blocks', () => {
        const blocks = parseDigestBlocks('- bullet one\n1. ranked one\n2. ranked two\n- bullet two')
        expect(blocks.map(block => [block.kind, block.ordered ?? false])).toEqual([
            ['list', false],
            ['list', true],
            ['list', false],
        ])
        expect(blocks[1].lines).toHaveLength(2)
    })
})
