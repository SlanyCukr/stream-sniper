import { Table } from 'react-bootstrap'
import SortableTableHeader from '@/components/common/SortableTableHeader'
import { formatTimeAgo } from '@/utils/dateUtils'
import {
    MIN_STREAMS_MAX, MIN_STREAMS_MIN,
} from '@/lib/creator/config'

const COLUMNS = [
    { key: 'streams', label: 'Streams attended', align: 'start' },
    { key: 'attendance', label: 'Attendance rate', align: 'end' },
    { key: 'last_seen', label: 'Last seen', align: 'end' },
    { key: 'messages', label: 'Messages', align: 'end' },
]

export const RegularsControls = ({
    minStreams, onMinStreamsChange, regularCount, totalStreams, showReadout,
}) => (
    <div className="regulars-controls">
        <label htmlFor="regulars-min-streams">Min streams attended</label>
        <input
            id="regulars-min-streams"
            type="number"
            min={MIN_STREAMS_MIN}
            max={MIN_STREAMS_MAX}
            className="form-control form-control-sm regulars-min-input"
            value={minStreams}
            onChange={onMinStreamsChange}
        />
        {showReadout ? (
            <span className="toolbar-readout">
                <strong>{regularCount}</strong> regulars of <strong>{totalStreams}</strong> streams
            </span>
        ) : null}
    </div>
)

const RegularsTable = ({
    regulars, totalStreams, sort, dir, onSort,
}) => (
    <div role="region" aria-label="Creator regulars" aria-live="polite">
        <Table hover responsive>
            <thead>
                <tr>
                    <th scope="col">#</th>
                    <th scope="col">Chatter</th>
                    {COLUMNS.map(column => (
                        <SortableTableHeader
                            key={column.key}
                            column={column}
                            sort={sort}
                            dir={dir}
                            onSort={onSort}
                        />
                    ))}
                </tr>
            </thead>
            <tbody>
                {regulars.map((regular, index) => (
                    <tr key={regular.chatterId}>
                        <td className="rank-num">{String(index + 1).padStart(2, '0')}</td>
                        <td>{regular.nick}</td>
                        <td style={{ minWidth: '140px' }}>
                            <span className="mono">{regular.streamsAttended?.toLocaleString()}</span>
                            <span className="data-bar" aria-hidden="true">
                                <span
                                    className="data-bar-fill"
                                    style={{
                                        width: `${Math.max(2, Math.round(((regular.streamsAttended || 0) / Math.max(1, totalStreams)) * 100))}%`,
                                    }}
                                />
                            </span>
                        </td>
                        <td className="mono text-end">{Math.round((regular.attendanceRate || 0) * 100)}%</td>
                        <td className="text-end">{regular.lastSeen ? formatTimeAgo(regular.lastSeen) : '--'}</td>
                        <td className="mono text-end">{regular.messageCount?.toLocaleString()}</td>
                    </tr>
                ))}
            </tbody>
        </Table>
    </div>
)

export default RegularsTable
