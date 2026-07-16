'use client'
import {
    createContext, useCallback, useContext, useEffect, useState,
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

const AuthContext = createContext()

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used within an AuthProvider')
    return context
}

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [token, setToken] = useState(null)
    const [isInitializing, setIsInitializing] = useState(true)
    const [sessionError, setSessionError] = useState(
        /** @type {ReturnType<typeof toUiFailure>|null} */ (null),
    )

    const clearSession = useCallback(() => {
        let storageFailure = null
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

    const establishSession = async sessionPromise => {
        const session = await sessionPromise
        storeToken(session.token)
        setToken(session.token)
        setUser(session.profile)
        setSessionError(null)
    }

    const runAuthAction = async (action, onFailure) => {
        try {
            await action()
        } catch (actionError) {
            const cleanupFailure = onFailure?.()
            if (cleanupFailure) setSessionError(cleanupFailure)
            throw actionError
        }
    }

    const login = (username, password) => runAuthAction(
        () => establishSession(authenticate(username, password)),
        clearSession,
    )
    const register = (username, email, password) => runAuthAction(
        () => establishSession(registerAndAuthenticate(username, email, password)),
    )
    const updateUser = userData => runAuthAction(
        async () => setUser(await updateProfile(userData)),
    )
    const changePassword = (currentPassword, newPassword) => runAuthAction(
        () => requestPasswordChange(currentPassword, newPassword),
    )
    const value = {
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
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext
