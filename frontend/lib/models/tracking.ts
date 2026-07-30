export interface CreateTrackedStreamerCommand {
    twitchUsername: string
    notes?: string | null
    isActive: boolean
    processingEnabled: boolean
}
