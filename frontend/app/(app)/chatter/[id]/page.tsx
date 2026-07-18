'use client'
import { use } from 'react'
import { notFound } from 'next/navigation'
import ChatterPassport from '@/views/chatter/ChatterPassport'

export default function ChatterPassportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const chatterId = Number(id)

  if (!Number.isSafeInteger(chatterId) || chatterId <= 0) {
    notFound()
  }

  return <ChatterPassport chatterId={chatterId} />
}
