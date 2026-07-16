// @ts-check

/**
 * @param {string|null|undefined} originalSrc
 * @param {string|number} width
 * @param {string|number} height
 * @returns {string|null}
 */
export const expandThumbnailUrl = (originalSrc, width, height) => originalSrc
    ? originalSrc.replace('%{width}', String(width)).replace('%{height}', String(height))
    : null
