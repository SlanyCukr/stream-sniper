'use client'

import {
    createContext, useContext, useState, useEffect, useCallback,
} from 'react'
import { jwtDecode } from 'jwt-decode'
import { api, setUnauthorizedHandler } from '@/lib/api'

const AuthContext = createContext()

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

export const AuthProvider = ({ children }) => {
    const [
        user,
        setUser,
    ] = useState(null)
    const [
        token,
        setToken,
    ] = useState(null)
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchUserInfo = useCallback(async authToken => {
        try {
            const { data } = await api.get('/auth/me', {
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                },
            })

            setUser(data)
            setError(null)
        } catch (fetchError) {
            console.error('Error fetching user info:', fetchError)
            setError('Failed to fetch user information')
            // Clear invalid token
            localStorage.removeItem('token')
            setToken(null)
            setUser(null)
        } finally {
            setLoading(false)
        }
    }, [
    ])

    const logout = useCallback(() => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
        setError(null)
    }, [
    ])

    // Route 401 responses from the shared api client through logout.
    useEffect(() => {
        setUnauthorizedHandler(() => {
            logout()
        })
    }, [
        logout,
    ])

    // Check for existing token on mount
    useEffect(() => {
        const savedToken = localStorage.getItem('token')
        if (savedToken) {
            try {
                const decodedToken = jwtDecode(savedToken)

                // Check if token is expired
                if (decodedToken.exp * 1000 > Date.now()) {
                    setToken(savedToken)
                    fetchUserInfo(savedToken)
                } else {
                    // Token expired, remove it
                    localStorage.removeItem('token')
                    setLoading(false)
                }
            } catch (tokenError) {
                console.error('Invalid token:', tokenError)
                localStorage.removeItem('token')
                setLoading(false)
            }
        } else {
            setLoading(false)
        }
    }, [
        fetchUserInfo,
    ])

    const login = async (username, password) => {
        try {
            setLoading(true)
            setError(null)

            const { data } = await api.post('/auth/login', {
                username,
                password,
            })
            const { access_token } = data

            // Store token
            localStorage.setItem('token', access_token)
            setToken(access_token)

            // Fetch user info
            await fetchUserInfo(access_token)

            return { success: true }
        } catch (loginError) {
            const message = loginError.response?.data?.detail || loginError.message || 'Login failed'
            console.error('Login error:', loginError)
            setError(message)
            return {
                success: false,
                error: message,
            }
        } finally {
            setLoading(false)
        }
    }

    const register = async (username, email, password) => {
        try {
            setLoading(true)
            setError(null)

            await api.post('/auth/register', {
                username,
                email,
                password,
            })

            // After registration, automatically log in
            return await login(username, password)
        } catch (registrationError) {
            const message = registrationError.response?.data?.detail || registrationError.message || 'Registration failed'
            console.error('Registration error:', registrationError)
            setError(message)
            return {
                success: false,
                error: message,
            }
        } finally {
            setLoading(false)
        }
    }

    const updateUser = async userData => {
        try {
            setLoading(true)
            setError(null)

            const { data } = await api.put('/auth/me', userData)
            setUser(data)
            return { success: true }
        } catch (updateError) {
            const message = updateError.response?.data?.detail || updateError.message || 'Update failed'
            console.error('Update error:', updateError)
            setError(message)
            return {
                success: false,
                error: message,
            }
        } finally {
            setLoading(false)
        }
    }

    const changePassword = async (currentPassword, newPassword) => {
        try {
            setLoading(true)
            setError(null)

            await api.put('/auth/me/password', {
                current_password: currentPassword,
                new_password: newPassword,
            })

            return { success: true }
        } catch (passwordChangeError) {
            const message = passwordChangeError.response?.data?.detail || passwordChangeError.message || 'Password change failed'
            console.error('Password change error:', passwordChangeError)
            setError(message)
            return {
                success: false,
                error: message,
            }
        } finally {
            setLoading(false)
        }
    }

    const isTokenExpired = useCallback(() => {
        if (!token) {
            return true
        }

        try {
            const decodedToken = jwtDecode(token)
            return decodedToken.exp * 1000 <= Date.now()
        } catch (tokenDecodeError) {
            console.error('Token decode error:', tokenDecodeError)
            return true
        }
    }, [
        token,
    ])

    const refreshUserInfo = useCallback(async () => {
        if (token && !isTokenExpired()) {
            await fetchUserInfo(token)
        }
    }, [
        token,
        isTokenExpired,
        fetchUserInfo,
    ])

    const isAuthenticated = !!(token && user && !isTokenExpired())
    const isAdmin = user?.role === 'admin'

    const value = {
        user,
        token,
        loading,
        error,
        isAuthenticated,
        isAdmin,
        login,
        register,
        logout,
        updateUser,
        changePassword,
        refreshUserInfo,
        isTokenExpired,
        clearError: () => setError(null),
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext
