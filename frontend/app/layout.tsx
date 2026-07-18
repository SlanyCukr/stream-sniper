import '@/styles/style.scss'
import type { Metadata } from 'next'
import { Providers } from './providers'
import LegacyHashRedirect from '@/components/layout/LegacyHashRedirect'

export const metadata: Metadata = {
  // Absolute-URL base for social metadata (og:image et al.). Without it, Next
  // resolves the generated opengraph-image routes against http://localhost:3000
  // in the standalone prod container, which breaks every social unfurl.
  metadataBase: new URL('https://stream-sniper.slanycukr.com'),
  title: 'Stream Sniper',
  description: 'Twitch stream analytics dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-bs-theme="dark">
      <body>
        <LegacyHashRedirect />
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
