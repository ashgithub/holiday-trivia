# System Patterns

## Architectural Patterns
- **Event-Driven Architecture**: Real-time events drive the application (question pushes, answer submissions, score updates)
- **Client-Server with WebSockets**: Bidirectional communication for real-time interactivity
- **Single Page Application (SPA)**: Frontend handles routing and state without full page reloads

## Communication Patterns
- **Publish-Subscribe**: Quiz master publishes questions, participants subscribe to receive them
- **Request-Response**: REST APIs for configuration and non-real-time operations
- **Streaming**: Continuous data flow for live drawing, answer aggregation, and score updates

## Data Patterns
- **In-Memory State**: Real-time game state managed in server memory during active sessions
- **Persistent Storage**: Questions and historical data stored in database (SQLite for simplicity)
- **Caching**: Frequently accessed data (current question, leaderboard) cached for performance

## UI Patterns
- **Role-Based Interfaces**: Different screens for quiz master vs participants
- **Real-Time Updates**: Automatic UI refreshes without user interaction
- **Progressive Enhancement**: Core functionality works without JavaScript, enhanced with real-time features

## Security Patterns
- **Input Validation**: Server-side validation of all user inputs
- **Rate Limiting**: Prevent spam answers during quiz sessions
- **Session Management**: Track participant sessions for scoring and state management

## Error Handling Patterns
- **Graceful Degradation**: Fall back to polling if WebSockets fail
- **User Feedback**: Clear error messages for connection issues, invalid inputs
- **Logging**: Comprehensive logging for debugging real-time issues

## Performance Patterns
- **Connection Pooling**: Efficient WebSocket connection management
- **Lazy Loading**: Load question data only when needed
- **Batch Updates**: Aggregate multiple events before sending to reduce network traffic

## Testing Patterns
- **Unit Testing**: Individual components (FastAPI routes, JS functions)
- **Integration Testing**: Full request/response cycles
- **Load Testing**: Simulate 150 concurrent users for scalability validation
- **Browser Testing**: Cross-browser compatibility for voice-to-text and WebSockets

## Deployment Patterns
- **Containerization**: Docker for consistent deployment
- **Environment Configuration**: Separate configs for development/production
- **Health Checks**: Monitor WebSocket connections and server performance
