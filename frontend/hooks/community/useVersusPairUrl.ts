import { useCallback } from 'react'
import { usePathname, useRouter } from 'next/navigation'

/**
 * Keep a versus matchup deep-linkable (`?a=&b=`) without triggering a
 * navigation/remount. Shared by the creator and chatter versus views so the
 * URL-sync rules cannot drift between them.
 */
export const useVersusPairUrl = () => {
    const router = useRouter()
    const pathname = usePathname()
    return useCallback((a: number | null, b: number | null) => {
        const params = new URLSearchParams()
        if (a) params.set('a', String(a))
        if (b) params.set('b', String(b))
        const query = params.toString()
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    }, [router, pathname])
}
