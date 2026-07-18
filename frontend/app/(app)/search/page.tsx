'use client'

import { Suspense } from 'react'
import SceneSearch from '@/views/scene/SceneSearch'

export default function SearchPage() {
  // SceneSearch reads ?q=&creator_id=&days= via useSearchParams, which requires
  // a Suspense boundary in the App Router to avoid a full-route client bailout.
  return (
    <Suspense fallback={null}>
      <SceneSearch />
    </Suspense>
  )
}
