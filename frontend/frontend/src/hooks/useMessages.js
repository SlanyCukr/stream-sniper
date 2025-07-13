import {
    useState, useEffect, useCallback,
} from 'react'
import {
    retrieveMessages,
    retrieveChatterOnStreamMessages,
} from '../api_utils'

/**
 * Custom hook for fetching messages from a specific chatter
 * @param {string|number} chatterId - The chatter ID
 * @returns {object} { data, loading, error, refetch }
 */
export const useMessages = chatterId => {
    const [
        data,
        setData,
    ] = useState([
    ])
    const [
        loading,
        setLoading,
    ] = useState(false)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchMessages = useCallback(async () => {
        if (!chatterId) {
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await retrieveMessages(chatterId)
            setData(response.data || [
            ])
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch messages')
        } finally {
            setLoading(false)
        }
    }, [
        chatterId,
    ])

    useEffect(() => {
        fetchMessages()
    }, [
        fetchMessages,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchMessages,
    }
}

/**
 * Custom hook for fetching messages from a specific chatter in a specific stream
 * @param {string|number} streamId - The stream ID
 * @param {string|number} chatterId - The chatter ID
 * @returns {object} { data, loading, error, refetch }
 */
export const useChatterStreamMessages = (streamId, chatterId) => {
    const [
        data,
        setData,
    ] = useState([
    ])
    const [
        loading,
        setLoading,
    ] = useState(false)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchMessages = useCallback(async () => {
        if (!streamId || !chatterId) {
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await retrieveChatterOnStreamMessages(streamId, chatterId)
            setData(response.data || [
            ])
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch chatter stream messages')
        } finally {
            setLoading(false)
        }
    }, [
        streamId,
        chatterId,
    ])

    useEffect(() => {
        fetchMessages()
    }, [
        fetchMessages,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchMessages,
    }
}
