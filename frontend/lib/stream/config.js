export const THUMBNAIL = {
    WIDTH: '300',
    HEIGHT: '170',
    DEFAULT_PLACEHOLDER: '/assets/images/no-thumbnail.png',
}

// Must match the backend sort whitelist: start|message_count|duration.
export const AVAILABLE_ORDERING = [
    { value: 'start', label: 'Started at' },
    { value: 'message_count', label: 'Num of messages' },
    { value: 'duration', label: 'Duration' },
]

export const DEFAULT_ORDERING = AVAILABLE_ORDERING[0]

// Keyset page size mirrors the backend default limit.
export const REPLAY_PAGE_SIZE = 100
