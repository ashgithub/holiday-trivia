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

### Strict Question Type Pattern
- **Canonical literal question.type convention**: All logic (frontend and backend) relies on the database value as the sole source of truth for each question type string (`pictionary`, `multiple_choice`, `fill_in_the_blank`, `word_cloud`, `wheel_of_fortune`, etc).
- **No normalization, mapping, or aliasing:** All UI, API, and backend logic (including drawing canvas, MCQ behavior, word cloud, etc) uses direct equality checking on the literal type (e.g. `if (type === 'pictionary') ...`).
- **Benefits:** Removes confusion, simplifies debugging, maintains a single source of truth for type handling.

### Similarity Scoring & Clustering Pattern (Word Cloud)

- **Goal:** For word cloud questions, automatically group similar answers using semantic embeddings without any admin intervention.
- **How it works:**
  - All free-text responses for a word cloud question are embedded into vectors using sentence-transformers (MiniLM or similar).
  - Answers are clustered or grouped based on cosine similarity (e.g., thresholded or via DBSCAN).
  - Each cluster “represents” a collective answer; its frequency/popularity is the count of members.
  - Scoring: Each participant receives points proportional to the size of their cluster (Score = 30 × participation ratio).
  - No correct answer is defined in the question; all logic is based on grouping.
  - Admin UI displays the cloud (words sized by cluster size), participant UI confirms score and popularity.
  - Library: sentence-transformers (pip install sentence-transformers), runs locally, fast.
- **Pattern fit:** Cleanly plugs into event-driven submission and update flow. No changes needed in persistent schema beyond allowing “blank answer” for word cloud questions.
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
