'use client'
import { use } from 'react'
import StreamCompare from '@/views/StreamCompare'

export default function ComparePage({ searchParams }: { searchParams: Promise<{ ids?: string }> }) {
  const { ids = '' } = use(searchParams)
  const initialIds = ids.split(',').map(Number).filter(id => Number.isInteger(id) && id > 0).slice(0, 4)
  return <StreamCompare initialIds={initialIds} />
}
