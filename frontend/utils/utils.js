export function chunks(arr, n) {
    let finalArr = [
    ]
    for (let i = 0; i < arr.length; i += n) {
        finalArr.push(arr.slice(i, i + n))
    }
    return finalArr
}

/**
 * Replaces `%{width}`, `%{height}` string in src with actual values.
 * @param {String} originalSrc
 * @returns
 */
export const findThumbnailSrc = (originalSrc, width, height) =>
    originalSrc ? originalSrc.replace('%{width}', width).replace('%{height}', height) : null
