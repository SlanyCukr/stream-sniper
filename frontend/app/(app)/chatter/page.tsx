'use client'
import { use } from 'react'
import ChatterExplorer from '@/views/chatter/ChatterExplorer'

export default function ChatterPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = use(searchParams)
  return <ChatterExplorer initialView={view === 'messages' ? 'messages' : 'footprint'} />
}
