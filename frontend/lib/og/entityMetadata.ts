/**
 * Page <Metadata> derived from the same card data that renders the OG images.
 *
 * The bespoke per-entity OG images (opengraph-image.tsx) shipped without any
 * generateMetadata, so every chatter/creator/stream link unfurled with the
 * generic app title/description — defeating the point of the custom cards.
 * This maps an OgCardData (already fetched, formatted, and truncated by
 * fetchOgData, which never throws) into title + description; a null card
 * (unknown id, dead backend) degrades to the layout defaults.
 */
import type { Metadata } from 'next'
import type { OgCardData } from '@/lib/og/fetchOgData'

export const buildEntityMetadata = (card: OgCardData | null): Metadata => {
  if (!card) return {}
  const description = [
    card.subtitle,
    card.stats.map(stat => `${stat.value} ${stat.label}`).join(' · '),
  ]
    .filter(Boolean)
    .join(' — ')
  return {
    title: card.title,
    ...(description ? { description } : {}),
  }
}
