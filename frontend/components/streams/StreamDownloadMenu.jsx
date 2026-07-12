'use client'
import { useState } from 'react'
import { Dropdown } from 'react-bootstrap'
import {
    downloadStreamExport,
    downloadStreamInsightCsv,
    getApiErrorMessage,
} from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

/**
 * Fetch a blob response and hand it to the browser as a file download.
 * The JWT lives only in localStorage (attached by the axios interceptor), so
 * a plain <a href> cannot be used for protected exports — fetch as a blob,
 * then click a programmatic object-URL anchor.
 * @param {object} response - axios response with a Blob body
 * @param {string} filename - suggested download filename
 */
const saveBlob = (response, filename) => {
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
}

/**
 * Resolve a download error to a UI message. With responseType: 'blob' axios
 * delivers error bodies as a Blob too, so the API's JSON {"detail": ...} must
 * be read back into a plain object before getApiErrorMessage can see it.
 * @param {unknown} downloadError - error thrown by an axios blob call
 * @returns {Promise<string>} safe message for the menu footer
 */
const getDownloadErrorMessage = async downloadError => {
    const body = downloadError?.response?.data
    if (body instanceof Blob) {
        try {
            downloadError.response.data = JSON.parse(await body.text())
        } catch {
            // Not JSON — fall through to the generic axios message.
        }
    }
    return getApiErrorMessage(downloadError, 'Download failed')
}

/**
 * Export dropdown for a stream: full chat log (NDJSON/CSV, login required)
 * and the aggregate emotes/phrases/mentions CSVs. All items download through
 * the axios blob helpers so the Authorization header is carried; items are
 * disabled while a download is in flight and errors surface in a menu footer.
 *
 * @param {object} props
 * @param {string|number} props.streamId
 * @param {string} [props.title] - stream title, used for the toggle aria-label
 */
const StreamDownloadMenu = ({ streamId, title }) => {
    const { token } = useAuth()
    const [
        downloading,
        setDownloading,
    ] = useState(null)
    const [
        errorMessage,
        setErrorMessage,
    ] = useState(null)

    /**
     * Run one download item: fetch the blob, save it, track in-flight state.
     * @param {string} key - item identifier for the in-flight state
     * @param {() => Promise<object>} fetcher - axios blob call
     * @param {string} filename - suggested download filename
     */
    const handleDownload = async (key, fetcher, filename) => {
        if (downloading) {
            return
        }
        setDownloading(key)
        setErrorMessage(null)
        try {
            const response = await fetcher()
            saveBlob(response, filename)
        } catch (downloadError) {
            setErrorMessage(await getDownloadErrorMessage(downloadError))
        } finally {
            setDownloading(null)
        }
    }

    const items = [
    ]
    if (token) {
        items.push(
            {
                key: 'chat-ndjson',
                label: 'Chat log (NDJSON)',
                icon: 'bi-file-earmark-text',
                fetcher: () => downloadStreamExport(streamId, 'ndjson'),
                filename: `stream_${streamId}_chat.ndjson`,
            },
            {
                key: 'chat-csv',
                label: 'Chat log (CSV)',
                icon: 'bi-filetype-csv',
                fetcher: () => downloadStreamExport(streamId, 'csv'),
                filename: `stream_${streamId}_chat.csv`,
            },
        )
    }
    items.push(
        {
            key: 'emotes-csv',
            label: 'Emotes CSV',
            icon: 'bi-filetype-csv',
            fetcher: () => downloadStreamInsightCsv(streamId, 'emotes'),
            filename: `stream_${streamId}_emotes.csv`,
        },
        {
            key: 'phrases-csv',
            label: 'Phrases CSV',
            icon: 'bi-filetype-csv',
            fetcher: () => downloadStreamInsightCsv(streamId, 'phrases'),
            filename: `stream_${streamId}_phrases.csv`,
        },
        {
            key: 'mentions-csv',
            label: 'Mentions CSV',
            icon: 'bi-filetype-csv',
            fetcher: () => downloadStreamInsightCsv(streamId, 'mentions'),
            filename: `stream_${streamId}_mentions.csv`,
        },
    )

    return (
        <Dropdown
            align="end"
            autoClose="outside">
            <Dropdown.Toggle
                variant="outline-primary"
                size="sm"
                aria-label={title ? `Export data for ${title}` : 'Export stream data'}>
                <i
                    className="bi bi-download me-2"
                    aria-hidden="true"></i>
                Export
            </Dropdown.Toggle>
            <Dropdown.Menu role="menu">
                {items.map(item => (
                    <Dropdown.Item
                        key={item.key}
                        role="menuitem"
                        disabled={Boolean(downloading)}
                        onClick={() => handleDownload(item.key, item.fetcher, item.filename)}>
                        <i
                            className={`bi ${item.icon} me-2`}
                            aria-hidden="true"></i>
                        {downloading === item.key ? 'Downloading...' : item.label}
                    </Dropdown.Item>
                ))}
                {errorMessage && (
                    <Dropdown.ItemText className="text-danger small">
                        {errorMessage}
                    </Dropdown.ItemText>
                )}
            </Dropdown.Menu>
        </Dropdown>
    )
}

export default StreamDownloadMenu
