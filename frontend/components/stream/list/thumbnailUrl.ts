export const expandThumbnailUrl = (
    originalSrc: string | null | undefined,
    width: string | number,
    height: string | number,
): string | null => originalSrc
    ? originalSrc.replace('%{width}', String(width)).replace('%{height}', String(height))
    : null
