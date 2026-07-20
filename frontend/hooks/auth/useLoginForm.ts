import { useAuth } from '@/contexts/AuthContext'
import { useAuthFormSubmit } from './useAuthFormSubmit'

interface LoginFormData {
    username: string
    password: string
}

const INITIAL_FORM: LoginFormData = {
    username: '',
    password: '',
}

const validate = (form: LoginFormData) => {
    if (!form.username.trim()) return 'Username is required'
    if (!form.password) return 'Password is required'
    return null
}

export const useLoginForm = (onSuccess?: () => void) => {
    const { login, isInitializing } = useAuth()
    return useAuthFormSubmit({
        initialForm: INITIAL_FORM,
        validate,
        submit: (form: LoginFormData) => login(form.username, form.password),
        failureMessage: 'Login failed',
        onSuccess,
        externallyDisabled: isInitializing,
    })
}
