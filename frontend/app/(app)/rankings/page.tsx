import type { Metadata } from 'next'
import Rankings from '@/views/scene/Rankings'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Chatter Rankings',
  description: 'Scene-wide chatter power rankings across the Czech Twitch scene.',
}

export default function RankingsPage() {
  return <Rankings />
}
