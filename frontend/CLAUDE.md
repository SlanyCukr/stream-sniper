# Stream Sniper Frontend - Developer Instructions

## Frontend-Specific Developer Instructions

Stream Sniper is a React-based frontend application for analyzing Twitch stream data and chat messages. The application provides functionality to browse streams, view chat messages, and analyze streamer/chatter interactions with a Twitch-like chat interface.

## Installation & Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## Architecture

### Technology Stack
- **Frontend Framework**: React 18.3.1
- **UI Library**: Bootstrap 5.1.3 + Reactstrap 9.0.0
- **Routing**: React Router DOM v6
- **Charts**: ApexCharts + React ApexCharts
- **HTTP Client**: Axios 1.7.7
- **Styling**: SASS 1.79.5
- **Build Tool**: React Scripts 5.0.1

### Backend Integration
- **API URL**: `http://localhost:5002` (configurable via environment)
- **Environment Management**: react-dotenv for runtime environment variables

## Project Structure

```
src/
├── App.js                    # Main application component
├── api_utils.js             # API utility functions
├── bettertv_emotes.js       # BetterTV emote integration
├── components/              # Reusable UI components
│   ├── ChatterSmallInfo.jsx
│   ├── Loader.jsx
│   ├── StreamThumbnail.jsx
│   ├── TwitchChatLookalike.jsx
│   └── dashboard/           # Dashboard-specific components
├── layouts/                 # Layout components
│   ├── FullLayout.js
│   ├── Header.js
│   ├── Logo.js
│   └── Sidebar.js
├── routes/                  # Application routing
│   └── Router.js
├── views/                   # Page components
│   ├── About.js
│   ├── Starter.js
│   └── ui/                  # Main application views
│       ├── AllStreams.jsx   # Stream browsing interface
│       ├── Stream.jsx       # Individual stream analysis
│       └── UserMessages.jsx # Chat message analysis
└── assets/                  # Static assets (images, styles)
```

## Key Features

### 1. Stream Management (`src/views/ui/AllStreams.jsx`)
- **Pagination**: 20 streams per page with full pagination controls
- **Filtering**: Filter by specific streamers/creators
- **Sorting**: Multiple ordering options (title, start time, message count, duration)
- **Stream Cards**: Visual thumbnails with metadata

### 2. Stream Analysis (`src/views/ui/Stream.jsx`)
- **Stream Details**: Comprehensive stream information
- **Chatter Selection**: Dropdown to select specific chatters
- **Message Analysis**: View messages from specific chatters during streams

### 3. Chat Interface (`src/components/TwitchChatLookalike.jsx`)
- **Twitch-Style Chat**: Mimics Twitch chat appearance
- **BetterTV Emotes**: Full integration with BetterTV emote system
- **Color Generation**: Random color assignment for usernames (avoiding yellow/green ranges)

### 4. User Message Analysis (`src/views/ui/UserMessages.jsx`)
- **Cross-Stream Analysis**: View messages from specific users across all streams
- **Message History**: Comprehensive chat message browsing

## API Endpoints (`src/api_utils.js`)

The application integrates with a backend API through the following endpoints:

```javascript
// Chatter-related endpoints
GET /chatter/${chatterId}/messages          # Get messages from specific chatter
GET /chatter/${nick}/chatter_id             # Get chatter ID by nickname

// Stream-related endpoints  
GET /streams?creator_id=${id}&offset=${offset}  # Get paginated streams
GET /stream/${streamId}                     # Get comprehensive stream data
GET /stream/${streamId}/chatters            # Get chatters in specific stream
GET /stream/${streamId}/chatter/${chatterId}/messages  # Get chatter messages in stream

// Creator endpoints
GET /creators                               # Get all available creators/streamers
```

## Development Commands

```bash
# Development server
npm start                                   # Start dev server on port 3000
npm start -- --port 3001                   # Start on custom port

# Building
npm run build                               # Production build
npm run build -- --analyze                 # Analyze bundle size

# Testing
npm test                                    # Run tests in watch mode
npm test -- --coverage                     # Run tests with coverage
npm test -- --watchAll=false               # Run tests once
npm test -- --verbose                      # Verbose test output

# Linting & Formatting
npm run lint                                # Run ESLint
npm run lint:fix                            # Fix ESLint issues
npm run format                              # Format code with Prettier

# Dependencies
npm install <package>                       # Install package
npm install --save-dev <package>           # Install dev dependency
npm update                                  # Update all packages
npm audit                                   # Check for vulnerabilities
npm audit fix                              # Fix vulnerabilities

# Docker development
docker-compose up frontend                  # Frontend container
docker-compose build frontend              # Rebuild frontend container
```

## Development Workflow

### Task Completion Protocol
**IMPORTANT**: After completing any development task, always commit and push changes immediately:

1. Complete the task implementation
2. Verify the build works: `npm run build`
3. Run tests if available: `npm test`
4. Stage and commit changes: `git add . && git commit -m "descriptive message"`
5. Push to remote: `git push`

This ensures all progress is saved and tracked in version control.

## React Development Patterns

### Component Structure
```jsx
// Functional component example
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const MyComponent = ({ title, data }) => {
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    // Side effects
  }, []);

  return (
    <div>
      <h2>{title}</h2>
      {loading ? <div>Loading...</div> : <div>{data}</div>}
    </div>
  );
};

MyComponent.propTypes = {
  title: PropTypes.string.isRequired,
  data: PropTypes.array
};

MyComponent.defaultProps = {
  data: []
};

export default MyComponent;
```

### API Integration
```jsx
// API hook example
import { useState, useEffect } from 'react';
import { fetchStreams } from '../api_utils';

const useStreams = (creatorId, offset = 0) => {
  const [streams, setStreams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadStreams = async () => {
      setLoading(true);
      try {
        const data = await fetchStreams(creatorId, offset);
        setStreams(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadStreams();
  }, [creatorId, offset]);

  return { streams, loading, error };
};
```

### State Management
```jsx
// Local state management
const [state, setState] = useState({
  data: [],
  loading: false,
  error: null
});

// Update state
setState(prevState => ({
  ...prevState,
  loading: true
}));
```

## Styling & UI Development

### SASS Structure
```scss
// Variables (_variables.scss)
$primary-color: #007bff;
$secondary-color: #6c757d;
$border-radius: 0.375rem;

// Component styles
.stream-card {
  border: 1px solid $secondary-color;
  border-radius: $border-radius;
  padding: 1rem;
  
  &:hover {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}
```

### Bootstrap Integration
```jsx
// Using Bootstrap classes
import { Card, Button, Container, Row, Col } from 'reactstrap';

const StreamCard = ({ stream }) => (
  <Card className="mb-3">
    <CardBody>
      <CardTitle tag="h5">{stream.title}</CardTitle>
      <Button color="primary" size="sm">
        View Stream
      </Button>
    </CardBody>
  </Card>
);
```

### Responsive Design
```jsx
// Responsive layout
<Container>
  <Row>
    <Col xs="12" md="8" lg="6">
      <StreamList streams={streams} />
    </Col>
    <Col xs="12" md="4" lg="6">
      <StreamFilters />
    </Col>
  </Row>
</Container>
```

## Testing Patterns

### Component Testing
```jsx
// Component test example
import { render, screen, fireEvent } from '@testing-library/react';
import StreamCard from '../StreamCard';

describe('StreamCard', () => {
  const mockStream = {
    id: 1,
    title: 'Test Stream',
    creator: 'TestUser'
  };

  test('renders stream title', () => {
    render(<StreamCard stream={mockStream} />);
    expect(screen.getByText('Test Stream')).toBeInTheDocument();
  });

  test('handles click events', () => {
    const handleClick = jest.fn();
    render(<StreamCard stream={mockStream} onClick={handleClick} />);
    
    fireEvent.click(screen.getByText('View Stream'));
    expect(handleClick).toHaveBeenCalledWith(mockStream);
  });
});
```

### API Testing
```jsx
// API mock example
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/streams', (req, res, ctx) => {
    return res(ctx.json({ streams: [] }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Configuration

### Environment Variables
```bash
# .env file
REACT_APP_API_URL=http://localhost:5002
REACT_APP_ENVIRONMENT=development
REACT_APP_VERSION=1.0.0

# Production .env
REACT_APP_API_URL=https://stream-sniper-api.slanycukr.com
REACT_APP_ENVIRONMENT=production
```

### Runtime Configuration
```javascript
// public/env.js
window.env = {
  API_URL: 'http://localhost:5002',
  ENVIRONMENT: 'development'
};

// Production configuration (automatic)
window.env = {
  API_URL: 'https://stream-sniper-api.slanycukr.com',
  ENVIRONMENT: 'production'
};
```

### BetterTV Integration
```javascript
// Emote usage example
import { getBetterTVEmotes } from './bettertv_emotes';

const emotes = getBetterTVEmotes();
const emoteUrl = `https://cdn.betterttv.net/emote/${emoteId}/1x`;
```

## Performance Optimization

### Code Splitting
```jsx
// Lazy loading components
import React, { Suspense, lazy } from 'react';

const StreamView = lazy(() => import('./views/ui/Stream'));
const AllStreams = lazy(() => import('./views/ui/AllStreams'));

// Usage with Suspense
<Suspense fallback={<div>Loading...</div>}>
  <StreamView />
</Suspense>
```

### Memoization
```jsx
// React.memo for expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  // Component logic
});

// useMemo for expensive calculations
const expensiveValue = useMemo(() => {
  return data.reduce((acc, item) => acc + item.value, 0);
}, [data]);

// useCallback for event handlers
const handleClick = useCallback((id) => {
  // Handle click
}, []);
```

## Component Architecture

### Layout System
- **FullLayout**: Main application wrapper with sidebar and header
- **Header**: Top navigation and branding
- **Sidebar**: Navigation menu for different sections
- **Logo**: Application branding component

### State Management
- Class-based components with local state management
- No external state management library (Redux, etc.)
- API calls managed through axios with promise-based handling

### Styling Approach
- SASS-based styling with modular architecture
- Bootstrap integration for responsive grid and components
- Custom variables and utilities in `src/assets/scss/`
- Component-specific styles co-located with components

## Key Dependencies Analysis

### Core Dependencies
- **React 18**: Latest React with concurrent features
- **Bootstrap 5**: Modern CSS framework with utility classes
- **Reactstrap**: Bootstrap components for React
- **React Router v6**: Modern routing with nested routes
- **Axios**: Promise-based HTTP client

### Development Tools
- **ESLint**: Code linting with React-specific rules
- **Babel**: JavaScript transpilation
- **SASS**: CSS preprocessing
- **Testing Library**: React component testing utilities

## Performance Considerations

### Code Splitting
- Lazy loading implemented for all route components
- React.lazy() used in `src/routes/Router.js`

### Data Handling
- Pagination for large datasets (20 items per page)
- Efficient API calls with offset-based pagination
- State management optimized for component lifecycle

### Asset Optimization
- Image assets organized by category (backgrounds, logos, users)
- SASS compilation for optimized CSS output

## Security Considerations

- No authentication system implemented in frontend
- API calls made to localhost (development setup)
- Environment variables properly separated from code
- No sensitive data stored in frontend state

## Common Frontend Tasks

### Adding New Component
1. Create component file in appropriate directory (`src/components/` or `src/views/`)
2. Add PropTypes validation
3. Implement responsive design with Bootstrap classes
4. Add SASS styles if needed
5. Write unit tests
6. Add to router if it's a page component

### Adding New API Integration
1. Add API function to `src/api_utils.js`
2. Create custom hook for data fetching
3. Add loading and error states
4. Implement caching if needed
5. Add API tests with MSW

### Adding New Route
1. Create page component in `src/views/`
2. Add route to `src/routes/Router.js`
3. Add navigation link to sidebar
4. Implement lazy loading if component is large

### Updating Styles
1. Use existing SASS variables from `src/assets/scss/_variables.scss`
2. Follow Bootstrap utility classes where possible
3. Add component-specific styles to component directory
4. Test responsive behavior on different screen sizes

### Performance Improvements
1. Identify expensive components with React DevTools
2. Add React.memo for components that re-render frequently
3. Use useMemo for expensive calculations
4. Implement virtual scrolling for large lists
5. Add code splitting for large components

## Debugging & Tools

### React DevTools
- Install React DevTools browser extension
- Use Profiler to identify performance bottlenecks
- Inspect component props and state

### Development Tools
```bash
# Bundle analyzer
npm run build -- --analyze

# ESLint
npm run lint

# Test coverage
npm test -- --coverage --watchAll=false
```

### Common Issues
1. **API Connection**: Check if backend is running on port 5002
2. **Authentication Issues**: 
   - Check JWT token expiration
   - Verify API authentication headers
   - Clear localStorage if tokens are corrupted
3. **Admin Access Issues**:
   - Verify user has admin role
   - Check admin route protection
   - Ensure proper API permissions
4. **CORS Issues**: Verify backend CORS configuration
5. **Build Errors**: Check for missing dependencies or syntax errors
6. **Performance**: Use React DevTools Profiler to identify bottlenecks
7. **Production Deployment**:
   - Check environment variables in production
   - Verify API URL configuration
   - Ensure Nginx configuration is correct

## Security Considerations

- **JWT Authentication**: Secure token-based authentication
- **Protected Routes**: Automatic redirection for unauthorized access
- **Role-based Access**: Different UI elements based on user roles
- **Token Storage**: Secure JWT token storage with automatic expiration
- **API Security**: Authentication headers automatically added to requests
- **Input Validation**: Form validation on authentication and admin forms
- **Environment Variables**: Properly separated configuration
- **No Sensitive Data**: No passwords or secrets stored in frontend state
- **Admin Protection**: Admin-only components and routes properly protected
- **XSS protection through React's built-in sanitization