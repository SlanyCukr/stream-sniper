export const formatTimelineClock = (timestamp: unknown): string => typeof timestamp === 'string' && timestamp.length >= 16
    ? timestamp.slice(11, 16)
    : ''
