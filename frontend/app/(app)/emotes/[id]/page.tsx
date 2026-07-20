import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import EmoteDetail from '@/views/scene/EmoteDetail'
import { parsePositiveId } from '@/utils/paramUtils'

// Server wrapper: validates the id (real 404 for garbage), static metadata —
// the emote name arrives client-side with the drill-down payload.
export const metadata: Metadata = {
  title: 'Emote drill-down',
  description: 'The lifetime story of one emote: usage, the channels it lives in, and its weekly trend.',
}

type PageProps = { params: Promise<{ id: string }> }

export default async function EmoteDetailPage({ params }: PageProps) {
  const { id } = await params
  const emoteId = parsePositiveId(id)

  if (emoteId == null) {
    notFound()
  }

  return <EmoteDetail emoteId={emoteId} />
}
