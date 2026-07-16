'use client'
import { use } from 'react'
import CopypastaPropagation from '@/views/scene/CopypastaPropagation'

export default function CopypastaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <CopypastaPropagation messageTextId={Number(id)} />
}
