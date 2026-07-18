import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Stream from '@/views/stream/Stream'
import { buildEntityMetadata } from '@/lib/og/entityMetadata'
import { fetchStreamOgData } from '@/lib/og/fetchOgData'

// Server component on purpose: generateMetadata cannot live in a 'use client' file,
// and the bespoke OG images are pointless while every stream link unfurls with the
// generic app title/description. The view itself stays a client component.

type PageProps = { params: Promise<{ id: string }> }

const parseStreamId = (raw: string): number | null => {
  const id = Number(raw)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  if (parseStreamId(id) == null) return {}
  return buildEntityMetadata(await fetchStreamOgData(id))
}

export default async function StreamPage({ params }: PageProps) {
  const { id } = await params
  const streamId = parseStreamId(id)

  if (streamId == null) {
    notFound()
  }

  return <Stream streamId={streamId} />
}
