'use client'

import { Dropdown } from 'react-bootstrap'
import { useStreamDownloads } from '@/hooks/stream/useStreamDownloads'

const StreamDownloadMenu = ({ streamId, title }) => {
    const downloads = useStreamDownloads(streamId)

    return (
        <Dropdown align="end" autoClose="outside">
            <Dropdown.Toggle
                variant="outline-primary"
                size="sm"
                aria-label={title ? `Export data for ${title}` : 'Export stream data'}
            >
                <i className="bi bi-download me-2" aria-hidden="true" />
                Export
            </Dropdown.Toggle>
            <Dropdown.Menu role="menu">
                {downloads.items.map(item => (
                    <Dropdown.Item
                        key={item.key}
                        role="menuitem"
                        disabled={Boolean(downloads.downloading)}
                        onClick={() => downloads.handleDownload(item)}
                    >
                        <i className={`bi ${item.icon} me-2`} aria-hidden="true" />
                        {downloads.downloading === item.key ? 'Downloading...' : item.label}
                    </Dropdown.Item>
                ))}
                {downloads.failure ? (
                    <Dropdown.ItemText className="text-danger small">
                        {downloads.failure.normalized.message}
                    </Dropdown.ItemText>
                ) : null}
            </Dropdown.Menu>
        </Dropdown>
    )
}

export default StreamDownloadMenu
