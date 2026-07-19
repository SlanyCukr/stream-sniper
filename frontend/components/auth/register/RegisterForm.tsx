'use client'

import { useRegisterForm } from '@/hooks/auth/useRegisterForm'
import AuthFormCard from '../shared/AuthFormCard'
import RegisterFields from './RegisterFields'

interface RegisterFormProps {
    onSwitchToLogin?: () => void
    onSuccess?: () => void
}

const RegisterForm = ({
    onSwitchToLogin, onSuccess,
}: RegisterFormProps) => {
    const {
        formData,
        errorMessage,
        isSubmitting,
        disabled,
        handleChange,
        handleSubmit,
    } = useRegisterForm(onSuccess)

    return (
        <AuthFormCard
            title="Create account"
            error={errorMessage}
            onSubmit={handleSubmit}
            disabled={disabled}
            isSubmitting={isSubmitting}
            submitLabel="Create Account"
            submittingLabel="Creating account..."
            switchLabel="Already have an account? Login here"
            onSwitch={onSwitchToLogin}
        >
            <RegisterFields
                formData={formData}
                onChange={handleChange}
                disabled={disabled}
            />
        </AuthFormCard>
    )
}

export default RegisterForm
