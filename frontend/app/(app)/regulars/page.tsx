import CreatorHub from '@/views/creator/CreatorHub'

export default async function RegularsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = await searchParams
  return <CreatorHub initialView={view === 'trends' ? 'trends' : 'regulars'} />
}
