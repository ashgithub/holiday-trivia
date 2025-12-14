# Technical Context

## Technology Stack
- **Backend**: Python 3.9+ with FastAPI framework
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no frameworks)
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time Communication**: WebSockets (via FastAPI WebSockets)
- **Voice-to-Text**: Browser native Speech Recognition API (Web Speech API)
- **Dependency Management**: uv for Python package management
- **Testing**: pytest, Locust for load testing, custom monitoring tools
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

> **All Python dependencies (install, upgrade, etc.) must use the [uv](https://github.com/astral-sh/uv) package manager. Never use pip, pip3, or python -m pip directly. All documentation, code, and installation instructions must always reference uv (e.g., `uv pip install sentence-transformers`).**

- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- websockets==12.0
- sqlalchemy==2.0.23 (ORM)
- alembic==1.12.1 (migrations)
- python-multipart==0.0.6
- **sentence-transformers==2.x** (semantic answer grouping and similarity for word cloud and pictionary questions)

#### Technical Design Note (Word Cloud/Pictionary Similarity)
- For word cloud (and pictionary) questions, all answers are embedded into vectors using sentence-transformers (MiniLM or similar).
- Answers are clustered by cosine similarity to identify semantically similar responses automatically.
- Scoring is assigned by cluster size; most popular (largest cluster) answers are displayed as largest in admin word cloud.
- *No correct answer is needed for word cloud questions in the admin UI or database—auto-scoring only.*
- Embedding model runs CPU-only, no GPU required, and is fast for short phrases.
- No frontend JS libraries are added; only backend changes.
### Frontend (JavaScript)
- No external libraries (pure JS)
- Web Speech API (native browser support)
- Canvas API for drawing
- Fetch API for REST calls
- WebSocket API for real-time

## Data Models
- **User**: id, name, role (quiz_master/participant), session_id
- **Question**: id, type, content, answers, correct_answer, category
  - **type**: always a literal string from canonical set: 'fill_in_the_blank', 'multiple_choice', 'pictionary', 'wheel_of_fortune', 'word_cloud'. No mapping in code.
- **Game**: id, status, current_question, participants, scores
- **Answer**: id, user_id, question_id, content, timestamp, correct

## API Endpoints
- `GET /api/` - API root with health info
- `GET /api/health` - Health check endpoint
- `WebSocket /ws/participant` - Participant real-time connection
- `WebSocket /ws/admin` - Quiz master real-time connection

## Real-time Message Types (15+ implemented)
- `quiz_started` - Quiz begins with progress info
- `question_pushed` - Question successfully pushed to participants
- `question` - New question broadcast with progress tracking
- `answer_received` - Admin notification of participant answers
- `personal_feedback` - Individual correctness feedback
- `answer_revealed` - Correct answer revealed to all participants
- `drawing_update` - Live drawing strokes from quiz master
- `timer_update` - Timer countdown updates
- `quiz_ended` - Quiz finished, cleanup state
- `status_update` - Real-time dashboard updates
- `questions_loaded` - Question library data sent to admin
- `question_added/deleted` - Question management confirmations

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
