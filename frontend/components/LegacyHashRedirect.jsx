'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export function LegacyHashRedirect() {
  const router = useRouter()
  useEffect(() => {
    const h = window.location.hash
    if (!h.startsWith('#/')) return
    let path = h.slice(1) || '/'
    // '#//evil.com' would produce a protocol-relative external redirect
    if (path.startsWith('//')) path = '/'
    // Routes that existed under the old HashRouter but moved in the migration
    if (path === '/all-streams' || path === '/starter') path = '/'
    router.replace(path)
  }, [
    router,
  ])
  return null
}

export default LegacyHashRedirect
