import { buildOgImage } from '@/lib/og/buildOgImage'
import { fetchChatterOgData } from '@/lib/og/fetchOgData'

// The prod frontend is an output:'standalone' Node server — render on Node, not edge.
export const runtime = 'nodejs'
export const alt = 'Stream Sniper chatter passport'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return buildOgImage(fetchChatterOgData, id, size)
}
