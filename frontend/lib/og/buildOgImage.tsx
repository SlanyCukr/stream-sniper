/**
 * Shared fetch -> fallback -> ImageResponse pipeline for the six OG card
 * surfaces: the three `opengraph-image.tsx` metadata images under
 * `app/(app)/*` and the three `/card/*` route handlers used for direct
 * embeds. Both call sites differ only in which `fetchOgData.ts` fetcher they
 * pass in, the rendered size, and (for the route handlers) a cache-control
 * header — everything else is identical, so it lives here once.
 */
import { ImageResponse } from 'next/og'
import { GENERIC_OG_CARD, type OgCardData } from '@/lib/og/fetchOgData'
import { OgCard } from '@/lib/og/ogCard'

type OgDataFetcher = (id: string) => Promise<OgCardData | null>

export async function buildOgImage(
  fetchOgData: OgDataFetcher,
  id: string,
  size: { width: number; height: number },
  cacheControl?: string,
): Promise<ImageResponse> {
  const data = (await fetchOgData(id)) ?? GENERIC_OG_CARD
  const image = new ImageResponse(<OgCard data={data} />, { ...size })
  if (cacheControl) image.headers.set('Cache-Control', cacheControl)
  return image
}
