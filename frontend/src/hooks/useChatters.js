import {
    useState, useEffect, useCallback,
} from 'react'
import {
    retrieveChattersOnStream,
    retrieveAllCreators,
    retrieveChatterId,
} from '../api_utils'

/**
 * Custom hook for fetching chatters on a specific stream
 * @param {string|number} streamId - The stream ID
 * @returns {object} { data, loading, error, refetch }
 */
export const useChatters = streamId => {
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

    const fetchChatters = useCallback(async () => {
        if (!streamId) {
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await retrieveChattersOnStream(streamId)
            setData(response.data || [
            ])
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch chatters')
        } finally {
            setLoading(false)
        }
    }, [
        streamId,
    ])

    useEffect(() => {
        fetchChatters()
    }, [
        fetchChatters,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchChatters,
    }
}

/**
 * Custom hook for fetching all creators
 * @returns {object} { data, loading, error, refetch }
 */
export const useCreators = () => {
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

    const fetchCreators = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            const response = await retrieveAllCreators()
            setData(response.data || [
            ])
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch creators')
        } finally {
            setLoading(false)
        }
    }, [
    ])

    useEffect(() => {
        fetchCreators()
    }, [
        fetchCreators,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchCreators,
    }
}

/**
 * Custom hook for fetching chatter ID by nickname
 * @param {string} nick - The chatter nickname
 * @param {boolean} enabled - Whether to execute the request (default: false)
 * @returns {object} { data, loading, error, refetch }
 */
export const useChatterId = (nick, enabled = false) => {
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

    const fetchChatterId = useCallback(async () => {
        if (!nick || !enabled) {
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await retrieveChatterId(nick)
            setData(response.data)
        } catch (err) {
            setError(err.response?.data?.message || err.message || 'Failed to fetch chatter ID')
        } finally {
            setLoading(false)
        }
    }, [
        nick,
        enabled,
    ])

    useEffect(() => {
        if (enabled) {
            fetchChatterId()
        }
    }, [
        fetchChatterId,
        enabled,
    ])

    return {
        data,
        loading,
        error,
        refetch: fetchChatterId,
    }
}
