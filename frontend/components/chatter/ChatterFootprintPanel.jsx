'use client'

import { useMemo } from 'react'
import { Table } from 'react-bootstrap'
import Link from 'next/link'
import { useChatterStreamActivity } from '@/hooks/chatter/useChattersQuery'
import ChatterPanelShell from './ChatterPanelShell'
import { formatStreamTimestamp } from '@/utils/dateUtils'

const ChatterFootprintPanel = ({ chatter }) => {
    const query = useChatterStreamActivity(chatter?.value || null)
    const activity = useMemo(() => query.data || [], [query.data])
    const maxMessages = useMemo(() => Math.max(1, ...activity.map(row => row.messageCount || 0)), [activity])
    const isLoading = Boolean(chatter?.value) && query.isLoading

    return (
        <ChatterPanelShell
            chatter={chatter}
            itemCount={activity.length}
            summaryCount={activity.length}
            summaryUnit="streams"
            isLoading={isLoading}
            error={query.error}
            onRetry={query.refetch}
            loadingText="Tracing chatter footprint..."
            errorTitle="Failed to load chatter footprint"
            awaitingHint="Search for a chatter nickname to see every captured stream they appear in."
            emptyTitle="No activity"
            emptyHint="This chatter has no recorded stream activity."
            regionLabel="Chatter footprint results"
        >
            <Table hover responsive>
                <thead>
                    <tr>
                        <th scope="col">Stream</th>
                        <th scope="col">Streamer</th>
                        <th scope="col">Started</th>
                        <th scope="col" className="text-end">Messages</th>
                    </tr>
                </thead>
                <tbody>
                    {activity.map(row => (
                        <tr key={row.streamId}>
                            <td><Link href={`/stream/${row.streamId}`}>{row.streamTitle}</Link></td>
                            <td>{row.creatorDisplayName}</td>
                            <td className="mono small">{formatStreamTimestamp(row.start)}</td>
                            <td className="mono text-end" style={{ minWidth: '110px' }}>
                                {row.messageCount.toLocaleString()}
                                <span className="data-bar" aria-hidden="true">
                                    <span
                                        className="data-bar-fill"
                                        style={{ width: `${Math.max(2, Math.round((row.messageCount / maxMessages) * 100))}%` }}
                                    />
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </Table>
        </ChatterPanelShell>
    )
}

export default ChatterFootprintPanel
