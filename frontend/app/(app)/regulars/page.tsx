'use client'
import { use } from 'react'
import StreamerRegulars from '@/views/StreamerRegulars'

export default function RegularsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = use(searchParams)
  return <StreamerRegulars initialView={view === 'trends' ? 'trends' : 'regulars'} />
}
