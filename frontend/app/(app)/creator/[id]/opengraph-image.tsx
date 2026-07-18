import { ImageResponse } from 'next/og'
import { fetchCreatorOgData, GENERIC_OG_CARD } from '@/lib/og/fetchOgData'
import { OgCard } from '@/lib/og/ogCard'

// The prod frontend is an output:'standalone' Node server — render on Node, not edge.
export const runtime = 'nodejs'
export const alt = 'Stream Sniper creator dossier'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = (await fetchCreatorOgData(id)) ?? GENERIC_OG_CARD
  return new ImageResponse(<OgCard data={data} />, { ...size })
}
