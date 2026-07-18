'use client'

import QueryState from '@/components/common/QueryState'
import TrendingRow, { type TrendingRowModel } from './TrendingRow'

/**
 * A synthetic React-Query-shaped result whose `data` is already projected into
 * presentation rows. Mirrors the `{ data, isLoading, error, refetch }` slice
 * `QueryState` consumes so the board can render loading / error / empty / table
 * without knowing whether the rows came from copypastas or emotes.
 */
export interface TrendingBoardQuery {
    data: TrendingRowModel[] | undefined
    isLoading: boolean
    error: unknown
    refetch: () => void
}

interface TrendingBoardProps {
    title: string
    /** Column heading for the entity ("Copypasta" | "Emote"). */
    primaryHeader: string
    /** Column heading for the trailing context chips ("Spread" | "Reach"). */
    contextHeader: string
    query: TrendingBoardQuery
    loadingText: string
    errorTitle: string
    emptyTitle: string
    emptyHint: string
}

const TrendingBoard = ({
    title,
    primaryHeader,
    contextHeader,
    query,
    loadingText,
    errorTitle,
    emptyTitle,
    emptyHint,
}: TrendingBoardProps) => (
    <section className="trending-board card">
        <div className="trending-board-head">
            <h2 className="trending-board-title">{title}</h2>
        </div>
        <QueryState
            query={query}
            errorTitle={errorTitle}
            loadingText={loadingText}
            loadingSize="md"
            isEmpty={(rows: TrendingRowModel[]) => rows.length === 0}
            emptyTitle={emptyTitle}
            emptyHint={emptyHint}
        >
            {(rows: TrendingRowModel[]) => {
                const maxUsage = Math.max(1, ...rows.map(row => row.currentUsage))
                return (
                    <div className="trending-table-wrap">
                        <table className="table trending-table">
                            <thead>
                                <tr>
                                    <th className="trending-th-rank">#</th>
                                    <th>{primaryHeader}</th>
                                    <th className="text-end">Now</th>
                                    <th>Trend</th>
                                    <th className="text-end">{contextHeader}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row, index) => (
                                    <TrendingRow
                                        key={row.key}
                                        rank={index + 1}
                                        row={row}
                                        maxUsage={maxUsage}
                                    />
                                ))}
                            </tbody>
                        </table>
                    </div>
                )
            }}
        </QueryState>
    </section>
)

export default TrendingBoard
