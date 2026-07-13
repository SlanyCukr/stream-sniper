'use client'
import { use } from 'react'
import CreatorDossier from '@/views/CreatorDossier'

export default function CreatorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <CreatorDossier creatorId={Number(id)} />
}
