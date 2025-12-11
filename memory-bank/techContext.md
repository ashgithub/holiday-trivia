# Technical Context

## Technology Stack
- **Backend**: Python 3.9+ with FastAPI framework
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no frameworks)
- **Database**: SQLite for development, PostgreSQL for production (if needed)
- **Real-time Communication**: WebSockets (via FastAPI WebSockets)
- **Voice-to-Text**: Browser native Speech Recognition API (Web Speech API)
- **Deployment**: Docker containerization, cloud hosting (AWS/GCP/Azure)

## Architecture Overview
```
┌─────────────────┐    WebSockets    ┌─────────────────┐
│   Quiz Master   │◄────────────────►│                 │
│     Client      │                  │                 │
└─────────────────┘                  │    FastAPI      │
                                     │    Backend      │
┌─────────────────┐    WebSockets    │                 │
│  Participant    │◄────────────────►│                 │
│    Clients      │                  │  - SQLite DB    │
│   (up to 150)   │                  │  - In-memory    │
└─────────────────┘                  │    State        │
                                     └─────────────────┘
```

## Key Components
- **WebSocket Manager**: Handles connection lifecycle, room management, message routing
- **Question Engine**: Manages question types, validation, scoring logic
- **State Manager**: Tracks active games, participant scores, current questions
- **Drawing Canvas**: Real-time collaborative drawing with stroke synchronization
- **Voice Handler**: Integrates Web Speech API for voice input

## Dependencies
### Backend (Python) - Managed by uv
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- websockets==12.0
- sqlalchemy==2.0.23 (ORM)
- alembic==1.12.1 (migrations)
- python-multipart==0.0.6

### Frontend (JavaScript)
- No external libraries (pure JS)
- Web Speech API (native browser support)
- Canvas API for drawing
- Fetch API for REST calls
- WebSocket API for real-time

## Data Models
- **User**: id, name, role (quiz_master/participant), session_id
- **Question**: id, type, content, answers, correct_answer, category
- **Game**: id, status, current_question, participants, scores
- **Answer**: id, user_id, question_id, content, timestamp, correct

## API Endpoints
- `GET /questions` - List configured questions
- `POST /questions` - Create new question
- `WebSocket /ws/game/{game_id}` - Real-time game communication
- `GET /game/{game_id}/status` - Current game state
- `POST /game/{game_id}/start` - Start quiz session

## Real-time Message Types
- `question_push`: New question broadcast
- `answer_submit`: Participant answer
- `score_update`: Leaderboard update
- `drawing_stroke`: Drawing coordinate data
- `game_state`: Status changes

## Performance Considerations
- WebSocket connection pooling
- Message batching for high-frequency updates
- In-memory caching for active games
- Database connection optimization
- CDN for static assets

## Browser Support
- Modern browsers with WebSocket support
- Web Speech API (Chrome, Edge, Safari)
- ES6+ JavaScript features
- Canvas 2D API for drawing
