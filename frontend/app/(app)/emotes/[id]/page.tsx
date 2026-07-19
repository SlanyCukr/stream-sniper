import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import EmoteDetail from '@/views/scene/EmoteDetail'

// Server wrapper: validates the id (real 404 for garbage), static metadata —
// the emote name arrives client-side with the drill-down payload.
export const metadata: Metadata = {
  title: 'Emote drill-down',
  description: 'The lifetime story of one emote: usage, the channels it lives in, and its weekly trend.',
}

type PageProps = { params: Promise<{ id: string }> }

const parseEmoteId = (raw: string): number | null => {
  const id = Number(raw)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export default async function EmoteDetailPage({ params }: PageProps) {
  const { id } = await params
  const emoteId = parseEmoteId(id)

  if (emoteId == null) {
    notFound()
  }

  return <EmoteDetail emoteId={emoteId} />
}
