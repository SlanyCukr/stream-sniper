'use client'
import { use } from 'react'
import Versus from '@/views/community/Versus'
import { parsePositiveId } from '@/utils/paramUtils'

export default function VersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = use(searchParams)
  return <Versus initialA={parsePositiveId(a)} initialB={parsePositiveId(b)} />
}
