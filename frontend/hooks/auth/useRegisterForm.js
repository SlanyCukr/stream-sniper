import { useAuth } from '@/contexts/AuthContext'
import { useAuthFormSubmit } from './useAuthFormSubmit'

const INITIAL_FORM = {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
}

const validateUsername = username => {
    if (!username.trim()) return 'Username is required'
    if (username.length < 3) return 'Username must be at least 3 characters long'
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        return 'Username can only contain letters, numbers, hyphens, and underscores'
    }
    return null
}

const validateEmail = email => {
    if (!email.trim()) return 'Email is required'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email address'
    return null
}

const validatePassword = form => {
    if (!form.password) return 'Password is required'
    if (form.password.length < 8) return 'Password must be at least 8 characters long'
    if (!/[A-Za-z]/.test(form.password)) return 'Password must contain at least one letter'
    if (!/[0-9]/.test(form.password)) return 'Password must contain at least one number'
    if (form.password !== form.confirmPassword) return 'Passwords do not match'
    return null
}

const validate = form => validateUsername(form.username) ||
    validateEmail(form.email) ||
    validatePassword(form)

export const useRegisterForm = onSuccess => {
    const { register, isInitializing } = useAuth()
    return useAuthFormSubmit({
        initialForm: INITIAL_FORM,
        validate,
        submit: form => register(form.username, form.email, form.password),
        failureMessage: 'Registration failed',
        onSuccess,
        externallyDisabled: isInitializing,
    })
}
