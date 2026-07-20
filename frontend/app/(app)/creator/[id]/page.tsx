import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import CreatorDossier from '@/views/creator/CreatorDossier'
import { buildEntityMetadata } from '@/lib/og/entityMetadata'
import { fetchCreatorOgData } from '@/lib/og/fetchOgData'
import { parsePositiveId } from '@/utils/paramUtils'

// Server component on purpose: generateMetadata cannot live in a 'use client' file,
// and the bespoke OG images are pointless while every creator link unfurls with the
// generic app title/description. The view itself stays a client component. The id is
// validated at the route boundary (mirrors stream/[id]) so /creator/not-a-number
// 404s instead of shipping a 200 with a client-side error alert.

type PageProps = { params: Promise<{ id: string }> }

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  if (parsePositiveId(id) == null) return {}
  return buildEntityMetadata(await fetchCreatorOgData(id))
}

export default async function CreatorPage({ params }: PageProps) {
  const { id } = await params
  const creatorId = parsePositiveId(id)

  if (creatorId == null) {
    notFound()
  }

  return <CreatorDossier creatorId={creatorId} />
}
