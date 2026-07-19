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
    // AuthContext.tsx is mid-migration and not yet typed upstream; assert the
    // subset of its value this hook relies on.
    const { login, isInitializing } = useAuth() as {
        login: (username: string, password: string) => Promise<void>
        isInitializing: boolean
    }
    return useAuthFormSubmit({
        initialForm: INITIAL_FORM,
        validate,
        submit: (form: LoginFormData) => login(form.username, form.password),
        failureMessage: 'Login failed',
        onSuccess,
        externallyDisabled: isInitializing,
    })
}
