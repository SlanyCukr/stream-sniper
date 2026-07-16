'use client'
import { use } from 'react'
import AudienceMovement from '@/views/creator/AudienceMovement'

export default function MovementPage({ searchParams }: { searchParams: Promise<{ creator?: string }> }) {
  const { creator } = use(searchParams)
  const creatorId = Number(creator)
  return <AudienceMovement initialCreatorId={Number.isInteger(creatorId) && creatorId > 0 ? creatorId : null} />
}
