import type { Metadata } from 'next'
import Radar from '@/views/scene/Radar'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Moment Radar',
  description: 'Live chat velocity across every currently-live Czech stream, spikes first.',
}

export default function RadarPage() {
  return <Radar />
}
