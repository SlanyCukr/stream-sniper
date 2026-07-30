import ChatterVersus from '@/views/community/ChatterVersus'
import { parsePositiveId } from '@/utils/paramUtils'

export default async function ChatterVersusPage({ searchParams }: { searchParams: Promise<{ a?: string, b?: string }> }) {
  const { a, b } = await searchParams
  return <ChatterVersus initialA={parsePositiveId(a)} initialB={parsePositiveId(b)} />
}
