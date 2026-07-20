'use client'
import { use } from 'react'
import AudienceMovement from '@/views/creator/AudienceMovement'
import { parsePositiveId } from '@/utils/paramUtils'

export default function MovementPage({ searchParams }: { searchParams: Promise<{ creator?: string }> }) {
  const { creator } = use(searchParams)
  return <AudienceMovement initialCreatorId={parsePositiveId(creator)} />
}
