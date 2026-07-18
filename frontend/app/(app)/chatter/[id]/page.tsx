import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import ChatterPassport from '@/views/chatter/ChatterPassport'
import { buildEntityMetadata } from '@/lib/og/entityMetadata'
import { fetchChatterOgData } from '@/lib/og/fetchOgData'

// Server component on purpose: generateMetadata cannot live in a 'use client' file,
// and the bespoke OG images are pointless while every chatter link unfurls with the
// generic app title/description. The view itself stays a client component.

type PageProps = { params: Promise<{ id: string }> }

const parseChatterId = (raw: string): number | null => {
  const id = Number(raw)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  if (parseChatterId(id) == null) return {}
  return buildEntityMetadata(await fetchChatterOgData(id))
}

export default async function ChatterPassportPage({ params }: PageProps) {
  const { id } = await params
  const chatterId = parseChatterId(id)

  if (chatterId == null) {
    notFound()
  }

  return <ChatterPassport chatterId={chatterId} />
}
