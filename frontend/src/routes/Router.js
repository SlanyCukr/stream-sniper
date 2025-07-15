import {
    lazy,
} from 'react'
import {
    Navigate,
} from 'react-router-dom'

/****Layouts*****/
const FullLayout = lazy(() => import('../layouts/FullLayout.js'))

/***** Pages ****/

const Starter = lazy(() => import('../views/Starter.js'))
const About = lazy(() => import('../views/About.js'))
const Alerts = lazy(() => import('../views/ui/Alerts'))
const Badges = lazy(() => import('../views/ui/Badges'))
const Buttons = lazy(() => import('../views/ui/Buttons'))
const Cards = lazy(() => import('../views/ui/Cards'))
const Grid = lazy(() => import('../views/ui/Grid'))
const Tables = lazy(() => import('../views/ui/Tables'))
const Forms = lazy(() => import('../views/ui/Forms'))
const Breadcrumbs = lazy(() => import('../views/ui/Breadcrumbs'))
const UserMessages = lazy(() => import('../views/ui/UserMessages.jsx'))
const AllStreams = lazy(() => import('../views/ui/AllStreams.jsx'))
const Stream = lazy(() => import('../views/ui/Stream.jsx'))

// Auth Pages
const Login = lazy(() => import('../views/auth/Login.jsx'))
const Profile = lazy(() => import('../views/auth/Profile.jsx'))

// Admin Pages
const AdminDashboard = lazy(() => import('../views/admin/AdminDashboard.jsx'))
const UserManagement = lazy(() => import('../views/admin/UserManagement.jsx'))
const CreateUser = lazy(() => import('../views/admin/CreateUser.jsx'))
const SystemInfo = lazy(() => import('../views/admin/SystemInfo.jsx'))
const AdminRoute = lazy(() => import('../components/admin/AdminRoute.jsx'))

/*****Routes******/

const ThemeRoutes = [
    // Auth routes (no layout)
    {
        path: '/login',
        element: <Login />,
    },
    // Main app routes (with layout)
    {
        path: '/',
        element: <FullLayout />,
        children: [
            {
                path: '/',
                element: <Navigate to="/starter" />,
            },
            {
                path: '/starter',
                element: <Starter />,
            },
            {
                path: '/about',
                element: <About />,
            },
            {
                path: '/alerts',
                element: <Alerts />,
            },
            {
                path: '/badges',
                element: <Badges />,
            },
            {
                path: '/buttons',
                element: <Buttons />,
            },
            {
                path: '/cards',
                element: <Cards />,
            },
            {
                path: '/grid',
                element: <Grid />,
            },
            {
                path: '/table',
                element: <Tables />,
            },
            {
                path: '/forms',
                element: <Forms />,
            },
            {
                path: '/breadcrumbs',
                element: <Breadcrumbs />,
            },
            {
                path: '/chatter-messages',
                element: <UserMessages />,
            },
            {
                path: '/all-streams',
                element: <AllStreams />,
            },
            {
                path: '/stream/:id',
                element: <Stream />,
            },
            {
                path: '/profile',
                element: <Profile />,
            },
            // Admin routes
            {
                path: '/admin',
                element: <AdminRoute><AdminDashboard /></AdminRoute>,
            },
            {
                path: '/admin/dashboard',
                element: <AdminRoute><AdminDashboard /></AdminRoute>,
            },
            {
                path: '/admin/users',
                element: <AdminRoute><UserManagement /></AdminRoute>,
            },
            {
                path: '/admin/users/create',
                element: <AdminRoute><CreateUser /></AdminRoute>,
            },
            {
                path: '/admin/system',
                element: <AdminRoute><SystemInfo /></AdminRoute>,
            },
        ],
    },
]

export default ThemeRoutes
