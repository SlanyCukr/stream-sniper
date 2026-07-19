'use client'

import { useState } from 'react'
import { Table } from 'react-bootstrap'
import Link from 'next/link'
import { useMessages } from '@/hooks/chatter/useMessagesQuery'
import Pagination from '@/components/common/pagination/Pagination'
import ChatterPanelShell from './ChatterPanelShell'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import { PAGINATION } from '@/lib/pagination/constants'
import type { ChatterOption } from '@/hooks/chatter/useChatterExplorer'

interface ChatterMessagesPanelProps {
    chatter: ChatterOption | null
}

const ChatterMessagesPanel = ({ chatter }: ChatterMessagesPanelProps) => {
    const [pageIndex, setPageIndex] = useState(PAGINATION.DEFAULT_OFFSET)
    // useMessages declares chatterId as non-nullable number, but internally
    // guards on Boolean(chatterId) — null (no chatter selected) is the real,
    // intended runtime value here.
    const query = useMessages((chatter?.value || null) as number, {
        pageIndex,
        pageSize: PAGINATION.MESSAGES_PER_PAGE,
    })
    const messages = query.data?.items || []
    const total = query.data?.total || 0
    const pageCount = query.data?.pageCount || 0
    const isLoading = Boolean(chatter?.value) && query.isLoading

    return (
        <ChatterPanelShell
            chatter={chatter}
            itemCount={messages.length}
            summaryCount={total}
            summaryUnit="messages"
            isLoading={isLoading}
            error={query.error}
            onRetry={query.refetch}
            loadingText="Loading chatter messages..."
            errorTitle="Failed to load chatter messages"
            awaitingHint="Search for a chatter nickname to read everything they have written across captured streams."
            emptyTitle="No messages"
            emptyHint="This chatter has no recorded messages."
            regionLabel="Chatter messages results"
        >
            <div className="visually-hidden">
                {`Showing ${messages.length} of ${total} messages on page ${pageIndex + 1} of ${pageCount}`}
            </div>
            <Table hover responsive>
                <thead>
                    <tr>
                        <th scope="col">Time</th>
                        <th scope="col">Streamer</th>
                        <th scope="col">Stream</th>
                        <th scope="col">Message</th>
                    </tr>
                </thead>
                <tbody>
                    {messages.map((message, rowIndex) => (
                        <tr key={`${pageIndex}-${rowIndex}`}>
                            <td className="mono small text-nowrap">{formatStreamTimestamp(message.timestamp)}</td>
                            <td>{message.creatorDisplayName}</td>
                            <td><Link href={`/stream/${message.streamId}`}>{message.streamTitle}</Link></td>
                            <td>{message.text}</td>
                        </tr>
                    ))}
                </tbody>
            </Table>
            <Pagination
                pageIndex={pageIndex}
                pageCount={pageCount}
                onPageChange={setPageIndex}
                ariaLabel="Chatter messages pagination"
            />
        </ChatterPanelShell>
    )
}

export default ChatterMessagesPanel
