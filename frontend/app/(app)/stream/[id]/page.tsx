'use client'
import { use } from 'react'
import { notFound } from 'next/navigation'
import Stream from '@/views/stream/Stream'

export default function StreamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const streamId = Number(id)

  if (!Number.isSafeInteger(streamId) || streamId <= 0) {
    notFound()
  }

  return <Stream streamId={streamId} />
}
