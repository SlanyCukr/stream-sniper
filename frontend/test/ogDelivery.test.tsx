import { beforeEach, describe, expect, it, vi } from 'vitest'

const ogMocks = vi.hoisted(() => ({
  calls: [] as Array<{
    element: { props?: { data?: unknown } }
    options: { width: number, height: number }
  }>,
  fetchChatter: vi.fn(),
  fetchCreator: vi.fn(),
  fetchStream: vi.fn(),
}))

vi.mock('next/og', () => ({
  ImageResponse: class MockImageResponse {
    headers = new Headers()

    constructor(
      element: { props?: { data?: unknown } },
      options: { width: number, height: number },
    ) {
      ogMocks.calls.push({ element, options })
    }
  },
}))

vi.mock('@/lib/og/fetchOgData', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/og/fetchOgData')>(),
  fetchChatterOgData: ogMocks.fetchChatter,
  fetchCreatorOgData: ogMocks.fetchCreator,
  fetchStreamOgData: ogMocks.fetchStream,
}))

import chatterImage, { size as chatterSize } from '@/app/(app)/chatter/[id]/opengraph-image'
import creatorImage, { size as creatorSize } from '@/app/(app)/creator/[id]/opengraph-image'
import streamImage, { size as streamSize } from '@/app/(app)/stream/[id]/opengraph-image'
import { GET as chatterCard } from '@/app/card/chatter/[id]/route'
import { GET as creatorCard } from '@/app/card/creator/[id]/route'
import { GET as streamCard } from '@/app/card/stream/[id]/route'
import { GENERIC_OG_CARD, type OgCardData } from '@/lib/og/fetchOgData'

const domainCard = (kind: string): OgCardData => ({
  kind,
  title: `${kind} title`,
  stats: [],
  tags: [],
})

const imageCases = [
  ['chatter', chatterImage, chatterSize, ogMocks.fetchChatter],
  ['creator', creatorImage, creatorSize, ogMocks.fetchCreator],
  ['stream', streamImage, streamSize, ogMocks.fetchStream],
] as const

const cardCases = [
  ['chatter', chatterCard, ogMocks.fetchChatter],
  ['creator', creatorCard, ogMocks.fetchCreator],
  ['stream', streamCard, ogMocks.fetchStream],
] as const

describe('public OG delivery contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ogMocks.calls.length = 0
  })

  it.each(imageCases)('%s metadata image forwards params, dimensions, and fallback', async (
    domain,
    renderImage,
    size,
    fetchData,
  ) => {
    const data = domainCard(domain)
    fetchData.mockResolvedValueOnce(data)

    const response = await renderImage({ params: Promise.resolve({ id: 'entity-42' }) })

    expect(fetchData).toHaveBeenCalledWith('entity-42')
    expect(size).toEqual({ width: 1200, height: 630 })
    expect(ogMocks.calls.at(-1)).toMatchObject({
      element: { props: { data } },
      options: { width: 1200, height: 630 },
    })
    expect(response.headers.get('Cache-Control')).toBeNull()

    fetchData.mockResolvedValueOnce(null)
    await renderImage({ params: Promise.resolve({ id: 'missing' }) })
    expect(ogMocks.calls.at(-1)?.element.props?.data).toBe(GENERIC_OG_CARD)
  })

  it.each(cardCases)('%s card route forwards params, fallback, dimensions, and cache policy', async (
    domain,
    getCard,
    fetchData,
  ) => {
    const data = domainCard(domain)
    fetchData.mockResolvedValueOnce(data)

    const response = await getCard(
      new Request(`https://example.test/card/${domain}/entity-42`),
      { params: Promise.resolve({ id: 'entity-42' }) },
    )

    expect(fetchData).toHaveBeenCalledWith('entity-42')
    expect(ogMocks.calls.at(-1)).toMatchObject({
      element: { props: { data } },
      options: { width: 1200, height: 630 },
    })
    expect(response.headers.get('Cache-Control')).toBe('public, max-age=300, s-maxage=3600')

    fetchData.mockResolvedValueOnce(null)
    await getCard(
      new Request(`https://example.test/card/${domain}/missing`),
      { params: Promise.resolve({ id: 'missing' }) },
    )
    expect(ogMocks.calls.at(-1)?.element.props?.data).toBe(GENERIC_OG_CARD)
  })
})
