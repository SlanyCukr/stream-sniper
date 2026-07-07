'use client'
import { use } from 'react'
import Stream from '@/views/Stream'

export default function StreamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <Stream streamId={id} />
}
