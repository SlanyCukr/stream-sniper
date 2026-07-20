/**
 * Strictly-positive integer from a route/query param, or null when absent or
 * invalid. The single parser behind every /:id route boundary and id-bearing
 * query param, so "what counts as a valid id" cannot drift per page.
 */
export const parsePositiveId = (raw: string | null | undefined): number | null => {
    const id = Number(raw)
    return Number.isSafeInteger(id) && id > 0 ? id : null
}
