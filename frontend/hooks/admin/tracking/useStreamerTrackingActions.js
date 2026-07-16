import { useActionFeedback } from '../shared/useActionFeedback'
import {
    useCreateTrackedStreamer,
    useDeleteTrackedStreamer,
    useUpdateTrackedStreamer,
} from './useTrackingQueries'

export const useStreamerTrackingActions = () => {
    const feedback = useActionFeedback()
    const createStreamer = useCreateTrackedStreamer()
    const updateStreamer = useUpdateTrackedStreamer()
    const deleteStreamer = useDeleteTrackedStreamer()

    const handleAddStreamer = streamer => feedback.runAction({
        action: () => createStreamer.mutateAsync(streamer),
        successMessage: 'Streamer added successfully',
        errorTitle: 'Failed to add streamer',
    })

    const handleToggleActive = (streamerId, currentStatus) => feedback.runAction({
        action: () => updateStreamer.mutateAsync({
            streamerId,
            changes: {
                is_active: !currentStatus,
            },
        }),
        successMessage: 'Streamer updated successfully',
        errorTitle: 'Failed to update streamer',
    })

    const handleToggleProcessing = (streamerId, currentStatus) => feedback.runAction({
        action: () => updateStreamer.mutateAsync({
            streamerId,
            changes: {
                processing_enabled: !currentStatus,
            },
        }),
        successMessage: 'Streamer updated successfully',
        errorTitle: 'Failed to update streamer',
    })

    const handleRemoveStreamer = streamerId => feedback.runAction({
        action: () => deleteStreamer.mutateAsync(streamerId),
        successMessage: 'Streamer removed successfully',
        errorTitle: 'Failed to remove streamer',
    })

    return {
        feedback,
        pending: {
            update: updateStreamer.isPending,
            delete: deleteStreamer.isPending,
        },
        commands: {
            addStreamer: handleAddStreamer,
            toggleActive: handleToggleActive,
            toggleProcessing: handleToggleProcessing,
            removeStreamer: handleRemoveStreamer,
        },
    }
}
