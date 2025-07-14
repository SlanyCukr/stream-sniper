/**
 * Application constants
 * 
 * This file contains all application-wide constants including
 * API configuration, pagination settings, UI dimensions, and other
 * configuration values used throughout the application.
 */

// API Configuration
export const API_CONFIG = {
    DEFAULT_URL: 'http://localhost:5002',
    TIMEOUT: 10000, // 10 seconds
    RETRY_ATTEMPTS: 3,
}

// Pagination Configuration
export const PAGINATION = {
    DEFAULT_OFFSET: 0,
    ITEMS_PER_PAGE: 20,
    MAX_VISIBLE_PAGES: 5,
}

// Thumbnail Configuration
export const THUMBNAIL = {
    WIDTH: '300',
    HEIGHT: '170',
    DEFAULT_PLACEHOLDER: '/assets/images/no-thumbnail.png',
}

// Chat Configuration
export const CHAT = {
    MAX_MESSAGES_DISPLAYED: 100,
    EMOTE_SIZE: '1x', // BetterTV emote size
    MESSAGE_CHUNK_SIZE: 50,
}

// Stream Ordering Options
export const AVAILABLE_ORDERING = [
    {
        value: 'title',
        label: 'Title',
    },
    {
        value: 'start',
        label: 'Started at',
    },
    {
        value: 'message_count',
        label: 'Num of messages',
    },
    {
        value: 'duration',
        label: 'Duration',
    },
]

// Default ordering option
export const DEFAULT_ORDERING = AVAILABLE_ORDERING[0]

// Color Generation
export const COLOR_CONFIG = {
    // Avoid yellow and green ranges for better readability
    EXCLUDED_HUE_RANGES: [
        {
            min: 40,
            max: 80,
        },   // Yellow range
        {
            min: 80,
            max: 140,
        },  // Green range
    ],
    SATURATION: {
        min: 60,
        max: 90,
    },
    LIGHTNESS: {
        min: 45,
        max: 75,
    },
}

// Loading States
export const LOADING_STATES = {
    IDLE: 'idle',
    LOADING: 'loading',
    SUCCESS: 'success',
    ERROR: 'error',
}

// Error Messages
export const ERROR_MESSAGES = {
    NETWORK_ERROR: 'Network error occurred. Please check your connection.',
    API_ERROR: 'Server error occurred. Please try again later.',
    NOT_FOUND: 'The requested resource was not found.',
    UNAUTHORIZED: 'You are not authorized to access this resource.',
    VALIDATION_ERROR: 'Please check your input and try again.',
    UNKNOWN_ERROR: 'An unexpected error occurred.',
}

// Query Keys for TanStack Query
export const QUERY_KEYS = {
    STREAMS: 'streams',
    CREATORS: 'creators',
    CHATTERS: 'chatters',
    MESSAGES: 'messages',
}

// Local Storage Keys
export const STORAGE_KEYS = {
    USER_PREFERENCES: 'stream_sniper_preferences',
    SELECTED_CREATOR: 'stream_sniper_selected_creator',
    PAGINATION_STATE: 'stream_sniper_pagination',
    THEME: 'stream_sniper_theme',
}

// Responsive Breakpoints (Bootstrap-based)
export const BREAKPOINTS = {
    XS: 0,
    SM: 576,
    MD: 768,
    LG: 992,
    XL: 1200,
    XXL: 1400,
}

// Animation Durations (in milliseconds)
export const ANIMATION = {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
    EXTRA_SLOW: 1000,
}

// Date/Time Formats (using date-fns format tokens)
export const DATE_FORMATS = {
    SHORT: 'MMM dd, yyyy',
    LONG: 'MMMM dd, yyyy HH:mm:ss',
    TIME_ONLY: 'HH:mm:ss',
    DATE_ONLY: 'yyyy-MM-dd',
    ISO: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
    STREAM_TIMESTAMP: 'yyyy/MM/dd HH:mm:ss', // Matches Moment format "YYYY/MM/DD HH:mm:ss"
}

// BetterTV Configuration
export const BETTERTV = {
    CDN_BASE_URL: 'https://cdn.betterttv.net/emote',
    EMOTE_SIZES: [
        '1x',
        '2x',
        '3x',
    ],
    DEFAULT_SIZE: '1x',
}

// Accessibility
export const ACCESSIBILITY = {
    FOCUS_OUTLINE_WIDTH: '2px',
    FOCUS_OUTLINE_COLOR: '#0066cc',
    MIN_TOUCH_TARGET: 44, // pixels
    MIN_COLOR_CONTRAST: 4.5, // WCAG AA standard
}
