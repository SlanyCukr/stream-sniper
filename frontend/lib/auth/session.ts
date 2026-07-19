import { jwtDecode } from 'jwt-decode'

const TOKEN_KEY = 'token'

class SessionStorageError extends Error {
    operation: string
    userFacing: true

    constructor(operation: string, cause: unknown) {
        super(`Unable to ${operation} stored authentication session`, { cause })
        this.name = 'SessionStorageError'
        this.operation = operation
        // Message is written for end users; normalizeApiError may render it.
        this.userFacing = true
    }
}

const accessSessionStorage = <T>(operation: string, action: () => T): T => {
    try {
        return action()
    } catch (storageError) {
        throw new SessionStorageError(operation, storageError)
    }
}

export const readStoredToken = (): string | null => accessSessionStorage(
    'read',
    () => localStorage.getItem(TOKEN_KEY),
)
export const storeToken = (token: string): void => accessSessionStorage(
    'write',
    () => localStorage.setItem(TOKEN_KEY, token),
)
export const removeStoredToken = (): void => accessSessionStorage(
    'clear',
    () => localStorage.removeItem(TOKEN_KEY),
)

export const isExpiredToken = (token: string | null | undefined): boolean => {
    if (!token) return true
    try {
        const decoded = jwtDecode(token)
        return !decoded.exp || decoded.exp * 1000 <= Date.now()
    } catch {
        return true
    }
}
