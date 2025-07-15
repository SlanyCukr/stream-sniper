import {
    createContext, useContext, useState, useEffect, useCallback,
} from 'react'
import PropTypes from 'prop-types'
import { jwtDecode } from 'jwt-decode'

// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api'

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

    const fetchUserInfo = useCallback(async authToken => {
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                },
            })

            if (response.ok) {
                const userData = await response.json()
                setUser(userData)
                setError(null)
            } else {
                throw new Error('Failed to fetch user info')
            }
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

    const login = async (username, password) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    password,
                }),
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
        } catch (loginError) {
            console.error('Login error:', loginError)
            setError(loginError.message)
            return {
                success: false,
                error: loginError.message,
            }
        } finally {
            setLoading(false)
        }
    }

    const register = async (username, email, password) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                }),
            })

            if (response.ok) {
                // After registration, automatically log in
                return await login(username, password)
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Registration failed')
            }
        } catch (registrationError) {
            console.error('Registration error:', registrationError)
            setError(registrationError.message)
            return {
                success: false,
                error: registrationError.message,
            }
        } finally {
            setLoading(false)
        }
    }

    const logout = useCallback(() => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
        setError(null)
    }, [
    ])

    const updateUser = async userData => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${API_URL}/auth/me`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
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
        } catch (updateError) {
            console.error('Update error:', updateError)
            setError(updateError.message)
            return {
                success: false,
                error: updateError.message,
            }
        } finally {
            setLoading(false)
        }
    }

    const changePassword = async (currentPassword, newPassword) => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${API_URL}/auth/me/password`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            })

            if (response.ok) {
                return { success: true }
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Password change failed')
            }
        } catch (passwordChangeError) {
            console.error('Password change error:', passwordChangeError)
            setError(passwordChangeError.message)
            return {
                success: false,
                error: passwordChangeError.message,
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

AuthProvider.propTypes = {
    children: PropTypes.node.isRequired,
}

export default AuthContext
