import { ImageResponse } from 'next/og'
import { fetchStreamOgData, GENERIC_OG_CARD } from '@/lib/og/fetchOgData'
import { OgCard } from '@/lib/og/ogCard'

// The prod frontend is an output:'standalone' Node server — render on Node, not edge.
export const runtime = 'nodejs'

/**
 * Embeddable stream card: a stable, linkable PNG of the OG card for pasting
 * into Discord/docs without relying on unfurl crawlers. Degrades to the
 * generic branded card for unknown ids or a dead backend — never a 500.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = (await fetchStreamOgData(id)) ?? GENERIC_OG_CARD
  const image = new ImageResponse(<OgCard data={data} />, { width: 1200, height: 630 })
  // Stats move with the rollups, not per-request: cache briefly in the browser,
  // longer at the edge/proxy.
  image.headers.set('Cache-Control', 'public, max-age=300, s-maxage=3600')
  return image
}
