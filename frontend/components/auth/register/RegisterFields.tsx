import type { ChangeEvent } from 'react'
import AuthFormField from '../shared/AuthFormField'

interface RegisterFormData {
    username: string
    email: string
    password: string
    confirmPassword: string
}

interface RegisterFieldsProps {
    formData: RegisterFormData
    onChange: (event: ChangeEvent<HTMLInputElement>) => void
    disabled?: boolean
}

const RegisterFields = ({
    formData, onChange, disabled,
}: RegisterFieldsProps) => (
    <>
        <AuthFormField
            label="Username"
            type="text"
            name="username"
            value={formData.username}
            onChange={onChange}
            placeholder="Choose a username (3-50 characters)"
            disabled={disabled}
            hint="Letters, numbers, hyphens, and underscores only"
        />
        <AuthFormField
            label="Email"
            type="email"
            name="email"
            value={formData.email}
            onChange={onChange}
            placeholder="Enter your email address"
            disabled={disabled}
        />
        <AuthFormField
            label="Password"
            type="password"
            name="password"
            value={formData.password}
            onChange={onChange}
            placeholder="Choose a password (8+ characters)"
            disabled={disabled}
            hint="Must contain at least one letter and one number"
        />
        <AuthFormField
            label="Confirm Password"
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={onChange}
            placeholder="Confirm your password"
            disabled={disabled}
        />
    </>
)

export default RegisterFields
