import { useAuth } from '@/contexts/AuthContext'
import { useAuthFormSubmit } from './useAuthFormSubmit'

const INITIAL_FORM = {
    username: '',
    password: '',
}

const validate = form => {
    if (!form.username.trim()) return 'Username is required'
    if (!form.password) return 'Password is required'
    return null
}

export const useLoginForm = onSuccess => {
    const { login, isInitializing } = useAuth()
    return useAuthFormSubmit({
        initialForm: INITIAL_FORM,
        validate,
        submit: form => login(form.username, form.password),
        failureMessage: 'Login failed',
        onSuccess,
        externallyDisabled: isInitializing,
    })
}
