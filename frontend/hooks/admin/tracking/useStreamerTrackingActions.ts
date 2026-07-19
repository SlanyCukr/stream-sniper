import { useState } from 'react'
import type { CreateTrackedStreamerRequest } from '@/lib/api/tracking'
import { useActionFeedback } from '../shared/useActionFeedback'
import {
    useCreateTrackedStreamer,
    useDeleteTrackedStreamer,
    useProbeTwitchChannel,
    useUpdateTrackedStreamer,
    type TwitchProbeResult,
} from './useTrackingQueries'

export const useStreamerTrackingActions = () => {
    const feedback = useActionFeedback()
    const createStreamer = useCreateTrackedStreamer()
    const updateStreamer = useUpdateTrackedStreamer()
    const deleteStreamer = useDeleteTrackedStreamer()
    const probeChannel = useProbeTwitchChannel()
    // Probe snapshots live only in memory: nothing is persisted server-side,
    // so results are keyed per streamer id and reset on unmount.
    const [probeResults, setProbeResults] = useState<Record<number, TwitchProbeResult>>({})
    const [probingId, setProbingId] = useState<number | null>(null)

    const handleAddStreamer = (streamer: CreateTrackedStreamerRequest) => feedback.runAction({
        action: () => createStreamer.mutateAsync(streamer),
        successMessage: 'Streamer added successfully',
        errorTitle: 'Failed to add streamer',
    })

    const handleToggleActive = (streamerId: number, currentStatus: boolean) => feedback.runAction({
        action: () => updateStreamer.mutateAsync({
            streamerId,
            changes: {
                is_active: !currentStatus,
            },
        }),
        successMessage: 'Streamer updated successfully',
        errorTitle: 'Failed to update streamer',
    })

    const handleToggleProcessing = (streamerId: number, currentStatus: boolean) => feedback.runAction({
        action: () => updateStreamer.mutateAsync({
            streamerId,
            changes: {
                processing_enabled: !currentStatus,
            },
        }),
        successMessage: 'Streamer updated successfully',
        errorTitle: 'Failed to update streamer',
    })

    const handleRemoveStreamer = (streamerId: number) => feedback.runAction({
        action: () => deleteStreamer.mutateAsync(streamerId),
        successMessage: 'Streamer removed successfully',
        errorTitle: 'Failed to remove streamer',
    })

    const handleProbeChannel = async (streamerId: number) => {
        setProbingId(streamerId)
        try {
            await feedback.runAction({
                action: async () => {
                    const result = await probeChannel.mutateAsync(streamerId)
                    setProbeResults(current => ({
                        ...current,
                        [streamerId]: result,
                    }))
                },
                errorTitle: 'Twitch probe failed',
            })
        } finally {
            setProbingId(null)
        }
    }

    return {
        feedback,
        pending: {
            update: updateStreamer.isPending,
            delete: deleteStreamer.isPending,
        },
        probe: {
            results: probeResults,
            probingId,
        },
        commands: {
            addStreamer: handleAddStreamer,
            toggleActive: handleToggleActive,
            toggleProcessing: handleToggleProcessing,
            removeStreamer: handleRemoveStreamer,
            probeChannel: handleProbeChannel,
        },
    }
}
