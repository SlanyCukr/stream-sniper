export const compareNullable = <T extends string | number>(
    left: T | null | undefined,
    right: T | null | undefined,
    direction: 'asc' | 'desc' = 'asc',
): number => {
    if (left == null && right == null) return 0
    if (left == null) return 1
    if (right == null) return -1
    const factor = direction === 'asc' ? 1 : -1
    if (left < right) return -factor
    if (left > right) return factor
    return 0
}
