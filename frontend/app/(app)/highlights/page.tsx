import type { Metadata } from 'next'
import Highlights from '@/views/scene/Highlights'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Highlights',
  description: 'The biggest chat moments across the Czech Twitch scene.',
}

export default function HighlightsPage() {
  return <Highlights />
}
