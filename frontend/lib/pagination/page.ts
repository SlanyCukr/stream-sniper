const toNonNegativeInteger = (value: unknown): number => (
    Number.isFinite(Number(value)) ? Math.max(0, Math.trunc(Number(value))) : 0
)

const toPositiveInteger = (value: unknown): number => (
    Number.isFinite(Number(value)) ? Math.max(1, Math.trunc(Number(value))) : 1
)

export const normalizePagination = (pageIndex: unknown = 0, pageSize: unknown = 20) => ({
    pageIndex: toNonNegativeInteger(pageIndex),
    pageSize: toPositiveInteger(pageSize),
})

export const getPageCount = (total: unknown, pageSize: unknown): number => {
    const safeTotal = toNonNegativeInteger(total)
    const safePageSize = toPositiveInteger(pageSize)
    return safeTotal === 0 ? 0 : Math.ceil(safeTotal / safePageSize)
}

export const getRowOffset = (pageIndex: unknown, pageSize: unknown): number => {
    const normalized = normalizePagination(pageIndex, pageSize)
    return normalized.pageIndex * normalized.pageSize
}

export const clampPageIndex = (pageIndex: unknown, pageCount: unknown): number => {
    const safePageIndex = toNonNegativeInteger(pageIndex)
    const safePageCount = toNonNegativeInteger(pageCount)
    return safePageCount === 0 ? 0 : Math.min(safePageIndex, safePageCount - 1)
}

export const createPage = <T>(items: T[], total: unknown, pageIndex: unknown, pageSize: unknown) => {
    const normalized = normalizePagination(pageIndex, pageSize)
    const safeTotal = toNonNegativeInteger(total)
    return {
        items: Array.isArray(items) ? items : [],
        total: safeTotal,
        ...normalized,
        pageCount: getPageCount(safeTotal, normalized.pageSize),
    }
}
