import type { ChangeEvent, ReactNode } from 'react'
import { Form } from 'react-bootstrap'

interface AuthFormFieldProps {
    label: string
    type: string
    name: string
    value: string
    onChange: (event: ChangeEvent<HTMLInputElement>) => void
    placeholder: string
    disabled?: boolean
    hint?: ReactNode
}

const AuthFormField = ({
    label,
    type,
    name,
    value,
    onChange,
    placeholder,
    disabled,
    hint = null,
}: AuthFormFieldProps) => (
    <Form.Group className="mb-3" controlId={name}>
        <Form.Label>{label}</Form.Label>
        <Form.Control
            type={type}
            name={name}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            disabled={disabled}
            required
        />
        {hint ? <small className="text-muted">{hint}</small> : null}
    </Form.Group>
)

export default AuthFormField
