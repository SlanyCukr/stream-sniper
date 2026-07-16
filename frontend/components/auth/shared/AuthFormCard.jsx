import {
    Alert, Button, Card, Form, Spinner,
} from 'react-bootstrap'

const AuthFormCard = ({
    title,
    error,
    onSubmit,
    disabled,
    isSubmitting,
    submitLabel,
    submittingLabel,
    switchLabel,
    onSwitch,
    children,
}) => (
    <Card className="auth-card">
        <Card.Header><h1 className="auth-mode">{title}</h1></Card.Header>
        <Card.Body>
            {error ? <Alert variant="danger" className="mb-3">{error}</Alert> : null}
            <Form onSubmit={onSubmit}>
                {children}
                <div className="d-grid gap-2">
                    <Button variant="primary" type="submit" disabled={disabled} size="lg">
                        {isSubmitting ? (
                            <>
                                <Spinner
                                    as="span"
                                    animation="border"
                                    size="sm"
                                    role="status"
                                    aria-hidden="true"
                                    className="me-2"
                                />
                                {submittingLabel}
                            </>
                        ) : submitLabel}
                    </Button>
                    {onSwitch ? (
                        <Button
                            variant="link"
                            onClick={onSwitch}
                            disabled={disabled}
                            className="text-decoration-none"
                        >
                            {switchLabel}
                        </Button>
                    ) : null}
                </div>
            </Form>
        </Card.Body>
    </Card>
)

export default AuthFormCard
