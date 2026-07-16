'use client'
import { use } from 'react'
import CreatorHub from '@/views/creator/CreatorHub'

export default function RegularsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = use(searchParams)
  return <CreatorHub initialView={view === 'trends' ? 'trends' : 'regulars'} />
}
