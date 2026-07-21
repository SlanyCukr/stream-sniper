export type ChatterView = 'messages' | 'footprint'

export const CHATTER_VIEWS = [
    { key: 'footprint', label: 'Footprint' },
    { key: 'messages', label: 'Messages' },
] as const satisfies ReadonlyArray<{ key: ChatterView, label: string }>
