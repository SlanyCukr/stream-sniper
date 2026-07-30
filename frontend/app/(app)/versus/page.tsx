import Versus from '@/views/community/Versus'
import { parsePositiveId } from '@/utils/paramUtils'

export default async function VersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = await searchParams
  return <Versus initialA={parsePositiveId(a)} initialB={parsePositiveId(b)} />
}
