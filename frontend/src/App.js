import { useRoutes } from 'react-router-dom'
import Themeroutes from './routes/Router'
import { AuthProvider } from './contexts/AuthContext'

const App = () => {
    const routing = useRoutes(Themeroutes)

    return (
        <AuthProvider>
            <div className="dark">{routing}</div>
        </AuthProvider>
    )
}

export default App
