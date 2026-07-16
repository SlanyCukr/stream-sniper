'use client'

import { useLoginForm } from '@/hooks/auth/useLoginForm'
import AuthFormCard from '../shared/AuthFormCard'
import LoginFields from './LoginFields'

const LoginForm = ({
    onSwitchToRegister, onSuccess,
}) => {
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
