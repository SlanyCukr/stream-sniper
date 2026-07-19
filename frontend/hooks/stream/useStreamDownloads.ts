import { useState } from 'react'
import type { AxiosResponse } from 'axios'
import { useAuth } from '@/contexts/AuthContext'
import {
    downloadStreamExport, downloadStreamInsightCsv,
} from '@/lib/api/streams'
import { toUiFailure, type UiFailure } from '@/utils/errorUtils'

interface DownloadItem {
    key: string
    label: string
    icon: string
    fetcher: () => Promise<AxiosResponse<Blob>>
    filename: string
}

const asRecord = (value: unknown): Record<string, unknown> | null => (
    typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null
)

const saveBlob = (response: AxiosResponse<Blob>, filename: string) => {
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
}

export const getDownloadFailure = async (downloadError: unknown): Promise<UiFailure> => {
    // downloadError's shape is unknown at the type level (thrown value); narrow
    // via asRecord before reading nested fields the way the runtime does.
    const errorRecord = asRecord(downloadError)
    const response = asRecord(errorRecord?.response)
    const body = response?.data
    if (body instanceof Blob) {
        try {
            const parsedBody: unknown = JSON.parse(await body.text())
            const parsedError = {
                ...errorRecord,
                response: {
                    ...response,
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

const streamDownloadItems = (streamId: number, authenticated: boolean): DownloadItem[] => {
    const items: DownloadItem[] = authenticated ? [
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

export const useStreamDownloads = (streamId: number) => {
    const { isAuthenticated } = useAuth()
    const [downloading, setDownloading] = useState<string | null>(null)
    const [failure, setFailure] = useState<UiFailure | null>(null)
    const handleDownload = async (item: DownloadItem) => {
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
