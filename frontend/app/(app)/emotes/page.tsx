import type { Metadata } from 'next'
import EmoteEconomy from '@/views/scene/EmoteEconomy'

// Server wrapper so the public listing page carries a real title/description in
// tabs and social unfurls; the view stays a client component.
export const metadata: Metadata = {
  title: 'Emote economy',
  description: 'Which emotes dominate the Czech Twitch scene, and how far they spread across channels.',
}

export default function EmotesPage() {
  return <EmoteEconomy />
}
