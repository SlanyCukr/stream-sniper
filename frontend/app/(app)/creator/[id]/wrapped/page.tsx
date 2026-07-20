import { notFound } from 'next/navigation'
import CreatorWrapped from '@/views/creator/CreatorWrapped'
import { parsePositiveId } from '@/utils/paramUtils'

// Server component on purpose (mirrors stream/[id]): the id is validated at the
// route boundary so /creator/not-a-number/wrapped 404s instead of rendering a
// plausible-looking "Nothing to wrap yet" empty recap. The view stays client.

type PageProps = { params: Promise<{ id: string }> }

export default async function CreatorWrappedPage({ params }: PageProps) {
  const { id } = await params
  const creatorId = parsePositiveId(id)

  if (creatorId == null) {
    notFound()
  }

  return <CreatorWrapped creatorId={creatorId} />
}
