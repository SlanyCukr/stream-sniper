# Stream Sniper Frontend

## Project Overview

Stream Sniper is a React-based frontend application for analyzing Twitch stream data and chat messages. The application provides functionality to browse streams, view chat messages, and analyze streamer/chatter interactions with a Twitch-like chat interface.

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
# Start development server
npm start

# Build production bundle
npm run build

# Run tests
npm test

# Eject from create-react-app (irreversible)
npm eject
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

## Modernization Progress

### Completed Phases

**Phase 1 (High Priority) ✅**
- React 19.1.0 upgrade
- React Router DOM 7.6.3 upgrade 
- Bootstrap 5.3.7 + React Bootstrap 2.10.10 migration
- TanStack Query 5.83.0 implementation
- Custom API hooks (useStreams, useStreamData, useCreators)

**Phase 2 (Medium Priority) ✅**
- ESLint configuration updated for React 19 compatibility
- React.memo optimizations for expensive components
- useMemo/useCallback performance optimizations
- Code splitting with React.lazy for heavy components
- WCAG 2.1 AA accessibility compliance
- Semantic HTML structure and proper heading hierarchy

**Phase 3 (Lower Priority) 🚧**
- ✅ Constants file for better organization (`src/constants.js`)
- ✅ PropTypes validation (all components properly validated)
- ✅ Moment.js → date-fns v4.1.0 migration
- 🚧 Enhanced error handling and loading states
- ⏳ Mobile responsiveness improvements

### Key Architectural Improvements

**Performance Optimizations:**
- Bundle optimization through code splitting
- Memoization patterns throughout component tree
- Efficient pagination with TanStack Query caching
- Eliminated Moment.js dependency (67KB reduction)

**Developer Experience:**
- Centralized constants management
- Modern date utilities with date-fns
- Comprehensive PropTypes validation
- ARIA compliance for accessibility

## Configuration

### Environment Variables
- **API_URL**: Backend API endpoint (default: `http://localhost:5002`)
- Configuration managed through `.env` file and `public/env.js`

### BetterTV Integration
- Emote data stored in `src/bettertv_emotes.js` and `src/bettertv_emotes.json`
- Python script `download_bettertv_emotes.py` for updating emote data
- CDN integration: `https://cdn.betterttv.net/emote/${emoteId}/1x`

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

## Future Enhancement Areas

1. **Authentication**: User login/logout system
2. **Real-time Updates**: WebSocket integration for live chat
3. **Advanced Filtering**: More sophisticated search and filter options
4. **Data Visualization**: Enhanced charts and analytics
5. **Mobile Optimization**: Responsive design improvements
6. **Performance**: Virtual scrolling for large message lists
7. **Accessibility**: ARIA labels and keyboard navigation