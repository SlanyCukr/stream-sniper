import CopypastaPropagation from '@/views/scene/CopypastaPropagation'

export default async function CopypastaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <CopypastaPropagation messageTextId={Number(id)} />
}
