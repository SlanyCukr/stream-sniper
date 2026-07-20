'use client'
import { use } from 'react'
import ChatterVersus from '@/views/community/ChatterVersus'
import { parsePositiveId } from '@/utils/paramUtils'

export default function ChatterVersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = use(searchParams)
  return <ChatterVersus initialA={parsePositiveId(a)} initialB={parsePositiveId(b)} />
}
