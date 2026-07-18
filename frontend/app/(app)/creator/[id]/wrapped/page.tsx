'use client'
import { use } from 'react'
import CreatorWrapped from '@/views/creator/CreatorWrapped'

export default function CreatorWrappedPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <CreatorWrapped creatorId={Number(id)} />
}
