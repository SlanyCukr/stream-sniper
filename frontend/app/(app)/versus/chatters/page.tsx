'use client'
import { use } from 'react'
import ChatterVersus from '@/views/community/ChatterVersus'

const parseChatterId = (raw: string | undefined): number | null => {
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export default function ChatterVersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = use(searchParams)
  return <ChatterVersus initialA={parseChatterId(a)} initialB={parseChatterId(b)} />
}
