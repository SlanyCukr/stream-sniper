import ChatterExplorer from '@/views/chatter/ChatterExplorer'

export default async function ChatterPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = await searchParams
  return <ChatterExplorer initialView={view === 'messages' ? 'messages' : 'footprint'} />
}
