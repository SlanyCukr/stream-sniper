import type { ChangeEvent } from 'react'
import AuthFormField from '../shared/AuthFormField'

interface LoginFormData {
    username: string
    password: string
}

interface LoginFieldsProps {
    formData: LoginFormData
    onChange: (event: ChangeEvent<HTMLInputElement>) => void
    disabled: boolean | undefined
}

const LoginFields = ({
    formData, onChange, disabled,
}: LoginFieldsProps) => (
    <>
        <AuthFormField
            label="Username"
            type="text"
            name="username"
            value={formData.username}
            onChange={onChange}
            placeholder="Enter your username"
            disabled={disabled}
        />
        <AuthFormField
            label="Password"
            type="password"
            name="password"
            value={formData.password}
            onChange={onChange}
            placeholder="Enter your password"
            disabled={disabled}
        />
    </>
)

export default LoginFields
