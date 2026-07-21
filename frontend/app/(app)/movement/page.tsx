import AudienceMovement from '@/views/creator/AudienceMovement'
import { parsePositiveId } from '@/utils/paramUtils'

export default async function MovementPage({ searchParams }: { searchParams: Promise<{ creator?: string }> }) {
  const { creator } = await searchParams
  return <AudienceMovement initialCreatorId={parsePositiveId(creator)} />
}
