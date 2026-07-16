import AuthFormField from '../shared/AuthFormField'

const LoginFields = ({
    formData, onChange, disabled,
}) => (
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
