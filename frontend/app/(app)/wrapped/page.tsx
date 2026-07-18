import type { Metadata } from 'next'
import Wrapped from '@/views/scene/Wrapped'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Scene Wrapped',
  description: 'A recap of the Czech Twitch scene: top creators, chatters, moments, copypastas, and emotes.',
}

export default function WrappedPage() {
  return <Wrapped />
}
