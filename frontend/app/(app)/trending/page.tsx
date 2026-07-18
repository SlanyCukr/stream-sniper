import type { Metadata } from 'next'
import Trending from '@/views/scene/Trending'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Trending',
  description: 'What is heating up across the Czech Twitch scene right now.',
}

export default function TrendingPage() {
  return <Trending />
}
