import {
    useState, useEffect, useCallback,
} from 'react'
import {
    retrieveStreams,
    retrieveStreamComprehensive,
} from '../api_utils'
import { PAGINATION } from '../constants'

/**
 * Custom hook for fetching paginated streams data
 * @param {number|null} creatorId - The creator ID to filter by (-1 for all)
 * @param {number} offset - The pagination offset
 * @returns {object} { data, loading, error, refetch }
 */
export const useStreams = (creatorId = -1, offset = 0) => {
    const [
        data,
        setData,
    ] = useState({
        streams: [
        ],
        max_offset: 0,
    })
    const [
        loading,
        setLoading,
    ] = useState(false)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchStreams = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            const response = await retrieveStreams(creatorId, offset * PAGINATION.ITEMS_PER_PAGE)
            setData(response.data || {
                streams: [
                ],
                max_offset: 0,
            })
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch streams')
        } finally {
            setLoading(false)
        }
    }, [
        creatorId,
        offset,
    ])

    useEffect(() => {
        fetchStreams()
    }, [
        fetchStreams,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchStreams,
    }
}

/**
 * Custom hook for fetching comprehensive stream data
 * @param {string|number} streamId - The stream ID
 * @returns {object} { data, loading, error, refetch }
 */
export const useStreamData = streamId => {
    const [
        data,
        setData,
    ] = useState(null)
    const [
        loading,
        setLoading,
    ] = useState(false)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchStreamData = useCallback(async () => {
        if (!streamId) {
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await retrieveStreamComprehensive(streamId)
            setData(response.data)
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch stream data')
        } finally {
            setLoading(false)
        }
    }, [
        streamId,
    ])

    useEffect(() => {
        fetchStreamData()
    }, [
        fetchStreamData,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchStreamData,
    }
}
