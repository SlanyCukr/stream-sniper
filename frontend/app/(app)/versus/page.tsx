'use client'
import { use } from 'react'
import Versus from '@/views/community/Versus'

const parseCreatorId = (raw: string | undefined): number | null => {
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export default function VersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = use(searchParams)
  return <Versus initialA={parseCreatorId(a)} initialB={parseCreatorId(b)} />
}
