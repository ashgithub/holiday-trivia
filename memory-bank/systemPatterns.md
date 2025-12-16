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

## Question Type Patterns
All logic uses literal DB `type` values (`pictionary`, `multiple_choice`, `fill_in_the_blank`, `word_cloud`, `wheel_of_fortune`) without normalization or mapping.

1. **fill_in_the_blank**: Multiple attempts, time-based scoring, voice/text input
2. **multiple_choice**: Single selection, time-based scoring, checkbox input
3. **wheel_of_fortune**: Live tile reveal (2s default), full-phrase guessing, time-based scoring
4. **word_cloud**: Semantic clustering (sentence-transformers), popularity scoring, no correct answer
5. **pictionary**: Drawing canvas, fuzzy similarity matching, time-based scoring

## Similarity Scoring & Clustering Pattern
- **Word Cloud**: Semantic clustering using sentence-transformers (MiniLM), cosine similarity thresholds, scoring proportional to cluster size
- **Pictionary**: Fuzzy matching for drawing guesses (cosine threshold 0.7)
- **Library**: sentence-transformers (CPU-only, local inference)

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
- **Unit Testing**: Individual components (FastAPI routes, JS functions, database models)
- **Integration Testing**: Full WebSocket communication cycles and database operations
- **Load Testing**: Comprehensive 150-user scenarios with performance monitoring and reporting
- **Browser Testing**: Cross-browser compatibility for voice-to-text and WebSocket features
- **Debug Logging**: Extensive client and server-side logging for real-time troubleshooting

## Deployment Patterns
- **Containerization**: Docker for consistent deployment
- **Environment Configuration**: Separate configs for development/production
- **Health Checks**: Monitor WebSocket connections and server performance
