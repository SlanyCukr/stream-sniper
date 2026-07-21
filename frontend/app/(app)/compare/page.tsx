import StreamCompare from '@/views/stream/StreamCompare'
import { parsePositiveId } from '@/utils/paramUtils'

export default async function ComparePage({ searchParams }: { searchParams: Promise<{ ids?: string }> }) {
  const { ids = '' } = await searchParams
  const initialIds = ids.split(',').map(raw => parsePositiveId(raw)).filter((id): id is number => id !== null).slice(0, 4)
  return <StreamCompare initialIds={initialIds} />
}
