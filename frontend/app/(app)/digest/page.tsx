import type { Metadata } from 'next'
import SceneDigest from '@/views/scene/SceneDigest'

// Server wrapper so the page carries a real title/description; the view stays
// a client component.
export const metadata: Metadata = {
  title: 'Scene digest',
  description: 'The Czech Twitch scene summarized: events, trending copypastas and emotes, top chatters, and the biggest moments.',
}

export default function DigestPage() {
  return <SceneDigest />
}
