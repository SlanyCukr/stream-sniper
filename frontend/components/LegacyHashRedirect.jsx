'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export function LegacyHashRedirect() {
  const router = useRouter()
  useEffect(() => {
    const h = window.location.hash
    if (h.startsWith('#/')) router.replace(h.slice(1) || '/')
  }, [
    router,
  ])
  return null
}

export default LegacyHashRedirect
