'use client'
import {
    createContext, useCallback, useContext, useEffect, useMemo, useState,
    type ReactNode,
} from 'react'
import { installUnauthorizedInterceptor } from '@/lib/api/client'
import {
    authenticate,
    fetchUserProfile,
    registerAndAuthenticate,
    requestPasswordChange,
    updateProfile,
} from '@/lib/auth/service'
import {
    isExpiredToken, readStoredToken, removeStoredToken, storeToken,
} from '@/lib/auth/session'
import { toUiFailure } from '@/utils/errorUtils'
import { isAdminRole } from '@/lib/auth/roles'
import type { AdminUserDto } from '@/lib/api/users'

type SessionFailure = ReturnType<typeof toUiFailure> | null

/** Shape resolved by `authenticate`/`registerAndAuthenticate` once the profile is hydrated. */
interface AuthSession {
    token: string
    profile: AdminUserDto
}

interface AuthContextValue {
    user: AdminUserDto | null
    isInitializing: boolean
    sessionError: SessionFailure
    isAuthenticated: boolean
    isAdmin: boolean
    login: (username: string, password: string) => Promise<void>
    register: (username: string, email: string, password: string) => Promise<void>
    logout: () => void
    updateUser: (userData: { email: string }) => Promise<void>
    changePassword: (currentPassword: string, newPassword: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const useAuth = (): AuthContextValue => {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used within an AuthProvider')
    return context
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<AdminUserDto | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [isInitializing, setIsInitializing] = useState(true)
    const [sessionError, setSessionError] = useState<SessionFailure>(null)

    const clearSession = useCallback((): SessionFailure => {
        let storageFailure: SessionFailure = null
        try {
            removeStoredToken()
        } catch (storageError) {
            storageFailure = toUiFailure(storageError, 'Failed to clear stored session')
        } finally {
            setToken(null)
            setUser(null)
        }
        return storageFailure
    }, [])

    const logout = useCallback(() => {
        setSessionError(clearSession())
    }, [clearSession])

    useEffect(() => installUnauthorizedInterceptor(logout), [logout])

    useEffect(() => {
        let active = true
        const restoreSession = async () => {
            try {
                const savedToken = readStoredToken()
                if (!savedToken) return
                if (isExpiredToken(savedToken)) {
                    setSessionError(clearSession())
                    return
                }
                const profile = await fetchUserProfile(savedToken)
                if (!active) return
                setToken(savedToken)
                setUser(profile)
                setSessionError(null)
            } catch (restoreError) {
                console.error('Unable to restore session')
                if (active) {
                    const cleanupFailure = clearSession()
                    setSessionError(
                        cleanupFailure ?? toUiFailure(restoreError, 'Failed to restore session'),
                    )
                }
            } finally {
                if (active) setIsInitializing(false)
            }
        }
        restoreSession()
        return () => {
            active = false
        }
    }, [clearSession])

    const establishSession = useCallback(async (sessionPromise: Promise<AuthSession>) => {
        const session = await sessionPromise
        storeToken(session.token)
        setToken(session.token)
        setUser(session.profile)
        setSessionError(null)
    }, [])

    const runAuthAction = useCallback(async (action: () => Promise<unknown>, onFailure?: () => SessionFailure) => {
        try {
            await action()
        } catch (actionError) {
            const cleanupFailure = onFailure?.()
            if (cleanupFailure) setSessionError(cleanupFailure)
            throw actionError
        }
    }, [])

    const login = useCallback((username: string, password: string) => runAuthAction(
        () => establishSession(authenticate(username, password)),
        clearSession,
    ), [runAuthAction, establishSession, clearSession])
    const register = useCallback((username: string, email: string, password: string) => runAuthAction(
        () => establishSession(registerAndAuthenticate(username, email, password)),
    ), [runAuthAction, establishSession])
    const updateUser = useCallback((userData: { email: string }) => runAuthAction(
        async () => setUser(await updateProfile(userData)),
    ), [runAuthAction])
    const changePassword = useCallback((currentPassword: string, newPassword: string) => runAuthAction(
        () => requestPasswordChange(currentPassword, newPassword),
    ), [runAuthAction])

    // Memoized so always-mounted chrome consuming useAuth() doesn't re-render
    // whenever an unrelated parent render rebuilds the provider.
    const value: AuthContextValue = useMemo(() => ({
        user,
        isInitializing,
        sessionError,
        isAuthenticated: Boolean(token && user && !isExpiredToken(token)),
        isAdmin: isAdminRole(user?.role),
        login,
        register,
        logout,
        updateUser,
        changePassword,
    }), [user, isInitializing, sessionError, token, login, register, logout, updateUser, changePassword])

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
