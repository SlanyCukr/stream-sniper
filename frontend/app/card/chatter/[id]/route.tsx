import { buildOgImage } from '@/lib/og/buildOgImage'
import { fetchChatterOgData } from '@/lib/og/fetchOgData'

// The prod frontend is an output:'standalone' Node server — render on Node, not edge.
export const runtime = 'nodejs'

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  // Stats move with the rollups, not per-request: cache briefly in the browser,
  // longer at the edge/proxy.
  return buildOgImage(fetchChatterOgData, id, { width: 1200, height: 630 }, 'public, max-age=300, s-maxage=3600')
}
