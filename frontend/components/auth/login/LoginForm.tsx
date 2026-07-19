'use client'

import { useLoginForm } from '@/hooks/auth/useLoginForm'
import AuthFormCard from '../shared/AuthFormCard'
import LoginFields from './LoginFields'

interface LoginFormProps {
    onSwitchToRegister: () => void
    onSuccess?: () => void
}

const LoginForm = ({
    onSwitchToRegister, onSuccess,
}: LoginFormProps) => {
    const login = useLoginForm(onSuccess)

    return (
        <AuthFormCard
            title="Sign in"
            error={login.errorMessage}
            onSubmit={login.handleSubmit}
            disabled={login.disabled}
            isSubmitting={login.isSubmitting}
            submitLabel="Login"
            submittingLabel="Logging in..."
            switchLabel="Don't have an account? Register here"
            onSwitch={onSwitchToRegister}
        >
            <LoginFields
                formData={login.formData}
                onChange={login.handleChange}
                disabled={login.disabled}
            />
        </AuthFormCard>
    )
}

export default LoginForm
