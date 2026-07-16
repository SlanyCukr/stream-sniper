import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
    downloadStreamExport, downloadStreamInsightCsv,
} from '@/lib/api/streams'
import { toUiFailure } from '@/utils/errorUtils'

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

export const getDownloadFailure = async downloadError => {
    const body = downloadError?.response?.data
    if (body instanceof Blob) {
        try {
            const parsedBody = JSON.parse(await body.text())
            const parsedError = {
                ...downloadError,
                response: {
                    ...downloadError.response,
                    data: parsedBody,
                },
            }
            return toUiFailure(downloadError, 'Download failed', parsedError)
        } catch {
            return toUiFailure(downloadError, 'Download failed')
        }
    }
    return toUiFailure(downloadError, 'Download failed')
}

const streamDownloadItems = (streamId, authenticated) => {
    const items = authenticated ? [
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
    ] : []
    return items.concat([
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
    ])
}

export const useStreamDownloads = streamId => {
    const { isAuthenticated } = useAuth()
    const [downloading, setDownloading] = useState(null)
    const [failure, setFailure] = useState(
        /** @type {ReturnType<typeof toUiFailure>|null} */ (null),
    )
    const handleDownload = async item => {
        if (downloading) return
        setDownloading(item.key)
        setFailure(null)
        try {
            saveBlob(await item.fetcher(), item.filename)
        } catch (downloadError) {
            setFailure(await getDownloadFailure(downloadError))
        } finally {
            setDownloading(null)
        }
    }

    return {
        items: streamDownloadItems(streamId, isAuthenticated),
        downloading,
        failure,
        handleDownload,
    }
}
