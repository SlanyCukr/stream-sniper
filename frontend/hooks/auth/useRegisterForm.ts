import { useAuth } from '@/contexts/AuthContext'
import { useAuthFormSubmit } from './useAuthFormSubmit'

interface RegisterFormData {
    username: string
    email: string
    password: string
    confirmPassword: string
}

const INITIAL_FORM: RegisterFormData = {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
}

const validateUsername = (username: string) => {
    if (!username.trim()) return 'Username is required'
    if (username.length < 3) return 'Username must be at least 3 characters long'
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        return 'Username can only contain letters, numbers, hyphens, and underscores'
    }
    return null
}

const validateEmail = (email: string) => {
    if (!email.trim()) return 'Email is required'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email address'
    return null
}

const validatePassword = (form: RegisterFormData) => {
    if (!form.password) return 'Password is required'
    if (form.password.length < 8) return 'Password must be at least 8 characters long'
    if (!/[A-Za-z]/.test(form.password)) return 'Password must contain at least one letter'
    if (!/[0-9]/.test(form.password)) return 'Password must contain at least one number'
    if (form.password !== form.confirmPassword) return 'Passwords do not match'
    return null
}

const validate = (form: RegisterFormData) => validateUsername(form.username) ||
    validateEmail(form.email) ||
    validatePassword(form)

export const useRegisterForm = (onSuccess?: () => void) => {
    const { register, isInitializing } = useAuth()
    return useAuthFormSubmit({
        initialForm: INITIAL_FORM,
        validate,
        submit: (form: RegisterFormData) => register(form.username, form.email, form.password),
        failureMessage: 'Registration failed',
        onSuccess,
        externallyDisabled: isInitializing,
    })
}
