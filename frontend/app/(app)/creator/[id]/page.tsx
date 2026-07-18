import type { Metadata } from 'next'
import CreatorDossier from '@/views/creator/CreatorDossier'
import { buildEntityMetadata } from '@/lib/og/entityMetadata'
import { fetchCreatorOgData } from '@/lib/og/fetchOgData'

// Server component on purpose: generateMetadata cannot live in a 'use client' file,
// and the bespoke OG images are pointless while every creator link unfurls with the
// generic app title/description. The view itself stays a client component.

type PageProps = { params: Promise<{ id: string }> }

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  if (!Number.isSafeInteger(Number(id)) || Number(id) <= 0) return {}
  return buildEntityMetadata(await fetchCreatorOgData(id))
}

export default async function CreatorPage({ params }: PageProps) {
  const { id } = await params
  return <CreatorDossier creatorId={Number(id)} />
}
