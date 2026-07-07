import '@/styles/style.scss'
import type { Metadata } from 'next'
import { Providers } from './providers'
import { LegacyHashRedirect } from '@/components/LegacyHashRedirect'

export const metadata: Metadata = {
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
