import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { jwtDecode } from 'jwt-decode'
import env from 'react-dotenv'

const AuthContext = createContext()

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [token, setToken] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

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
            } catch (error) {
                console.error('Invalid token:', error)
                localStorage.removeItem('token')
                setLoading(false)
            }
        } else {
            setLoading(false)
        }
    }, [])

    const fetchUserInfo = useCallback(async (authToken) => {
        try {
            const response = await fetch(`${env.API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            })

            if (response.ok) {
                const userData = await response.json()
                setUser(userData)
                setError(null)
            } else {
                throw new Error('Failed to fetch user info')
            }
        } catch (error) {
            console.error('Error fetching user info:', error)
            setError('Failed to fetch user information')
            // Clear invalid token
            localStorage.removeItem('token')
            setToken(null)
            setUser(null)
        } finally {
            setLoading(false)
        }
    }, [])

    const login = async (username, password) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${env.API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            })

            if (response.ok) {
                const data = await response.json()
                const { access_token } = data
                
                // Store token
                localStorage.setItem('token', access_token)
                setToken(access_token)
                
                // Fetch user info
                await fetchUserInfo(access_token)
                
                return { success: true }
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Login failed')
            }
        } catch (error) {
            console.error('Login error:', error)
            setError(error.message)
            return { success: false, error: error.message }
        } finally {
            setLoading(false)
        }
    }

    const register = async (username, email, password) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${env.API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, email, password }),
            })

            if (response.ok) {
                const userData = await response.json()
                // After registration, automatically log in
                return await login(username, password)
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Registration failed')
            }
        } catch (error) {
            console.error('Registration error:', error)
            setError(error.message)
            return { success: false, error: error.message }
        } finally {
            setLoading(false)
        }
    }

    const logout = useCallback(() => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
        setError(null)
    }, [])

    const updateUser = async (userData) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${env.API_URL}/auth/me`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(userData),
            })

            if (response.ok) {
                const updatedUser = await response.json()
                setUser(updatedUser)
                return { success: true }
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Update failed')
            }
        } catch (error) {
            console.error('Update error:', error)
            setError(error.message)
            return { success: false, error: error.message }
        } finally {
            setLoading(false)
        }
    }

    const changePassword = async (currentPassword, newPassword) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${env.API_URL}/auth/me/password`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    current_password: currentPassword, 
                    new_password: newPassword 
                }),
            })

            if (response.ok) {
                return { success: true }
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Password change failed')
            }
        } catch (error) {
            console.error('Password change error:', error)
            setError(error.message)
            return { success: false, error: error.message }
        } finally {
            setLoading(false)
        }
    }

    const isTokenExpired = useCallback(() => {
        if (!token) return true
        
        try {
            const decodedToken = jwtDecode(token)
            return decodedToken.exp * 1000 <= Date.now()
        } catch (error) {
            return true
        }
    }, [token])

    const refreshUserInfo = useCallback(async () => {
        if (token && !isTokenExpired()) {
            await fetchUserInfo(token)
        }
    }, [token, isTokenExpired, fetchUserInfo])

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