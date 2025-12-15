# All-Hands Holiday Trivia 🎄

An interactive real-time holiday trivia game for Zoom all-hands meetings with up to 150 participants. Features multiple question types, live drawing, voice input, comprehensive admin controls, and Christmas-themed UI.

## Features

- **Multiple Question Types**: Fill-in-the-blank, word cloud, live drawing, wheel of fortune, multiple choice
- **Real-time Interaction**: WebSocket-based communication for instant responses
- **Voice Input**: Browser-native speech-to-text support
- **Live Drawing**: Real-time collaborative drawing for quiz master
- **Christmas Theme**: Festive UI with subtle holiday styling
- **Scalable**: Supports up to 150 concurrent participants
- **Advanced Admin Panel**: Password-protected quiz master controls with question management
- **Question Library**: Categorized question management with summary statistics
- **Load Testing**: Comprehensive 150-user performance testing infrastructure
- **Real-time Analytics**: Live participant tracking and answer statistics
- **Robust Error Handling**: Debug logging and graceful failure recovery

## Tech Stack

- **Backend**: Python 3.9+ with FastAPI
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Database**: SQLite (development) / PostgreSQL (production)
- **Real-time**: WebSockets
- **Voice**: Web Speech API

## Quick Start

### Prerequisites
- Python 3.9+
- Modern web browser with WebSocket support

### Installation

1. **Clone the repository** (if applicable) or navigate to project directory

2. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Populate sample quiz questions** (optional, for testing):
   ```bash
   uv run populate_sample_data.py
   ```

5. **Start the server**:
   ```bash
   uv run python backend/main.py
   ```
   Server will start on http://localhost:8000

### Usage

1. **For Participants**: Open http://localhost:8000 in web browser
2. **For Trivia Master**: Open http://localhost:8000/admin and login with password `quizzer`

### Sample Data

The project includes a comprehensive sample dataset with 25 questions across 5 categories:
- **Geography**: 5 questions (capitals, landmarks, countries)
- **Science**: 8 questions (physics, biology, chemistry, space)
- **History**: 5 questions (events, figures, timelines)
- **General**: 7 questions (mixed knowledge topics)

Run `uv run populate_sample_data.py` to populate the database with sample questions for testing.

### Question Export/Import

The application includes comprehensive CLI tools and web-based interfaces for managing question data:

#### CLI Tools

**Export Questions:**
```bash
# Export all questions
uv run python export_questions.py questions.json

# Export by category
uv run python export_questions.py geography_questions.json --category geography

# Export by question type
uv run python export_questions.py mc_questions.json --type multiple_choice

# Export in compact format
uv run python export_questions.py questions_compact.json --compact
```

**Import Questions:**
```bash
# Import questions (dry run first)
uv run python import_questions.py questions.json --dry-run

# Import with duplicate handling
uv run python import_questions.py questions.json --skip-duplicates

# Update existing questions instead of skipping
uv run python import_questions.py questions.json --update-existing

# Replace all questions (WARNING: deletes all existing questions!)
uv run python import_questions.py questions.json --drop-existing
```

#### Web Interface

Use the **Data Management** tab in the admin interface (`/admin`) for:
- **Export**: Click "Export Questions" to download all questions as JSON
- **Import**: Select a JSON file, choose options, and click "Import Questions"
- **Validation**: Automatic validation with detailed error messages

#### JSON Format

Questions are exported/imported as JSON arrays with this structure:
```json
[
  {
    "id": 1,
    "type": "multiple_choice",
    "content": "What is 2+2?",
    "answers": ["3", "4", "5", "6"],
    "correct_answer": "4",
    "category": "math",
    "allow_multiple": false,
    "order": 0,
    "created_at": "2025-12-15T12:00:00.000000"
  }
]
```

#### Features

- **Validation**: Comprehensive validation of question types, required fields, and data integrity
- **Duplicate Handling**: Options to skip, update, or allow duplicates during import
- **Filtering**: Export specific categories or question types
- **Statistics**: Detailed import/export statistics and progress reporting
- **Error Recovery**: Graceful handling of malformed data with specific error messages
- **Legacy Support**: Automatic conversion of old question type names

### Database Switching

The application supports switching between different SQLite databases dynamically from the admin interface:

- **Database Selection**: Choose from available database files in the Settings tab
- **Connection Preservation**: Participants stay connected during database switches
- **Graceful Transitions**: Active trivia sessions end cleanly before switching
- **Multiple Databases**: Support for production, development, and backup databases

### During Zoom Meeting

1. Trivia master shares their screen showing the admin panel
2. Participants join via the participant page URL
3. Trivia master adds questions and controls the game flow
4. Real-time answers and scores are displayed

## Project Structure

```
all-hands-game/
├── backend/
│   ├── main.py              # FastAPI server with WebSocket handlers
│   ├── models.py            # Database models (User, Question, Game, Answer)
│   └── pyproject.toml       # Backend package configuration
├── frontend/
│   ├── index.html           # Participant page with voice input
│   ├── admin.html           # Quiz master page with controls
│   ├── styles.css           # Christmas-themed styles with animations
│   ├── app.js               # Participant client logic
│   └── admin.js             # Admin client with question management
├── tests/
│   ├── unit_tests/          # Database and business logic tests
│   ├── integration_tests/   # WebSocket and API endpoint tests
│   └── load_tests/          # 150-user performance testing
│       ├── locustfile.py    # Locust load testing framework
│       ├── monitoring.py    # System monitoring utilities
│       └── test_scenarios.py # Comprehensive test scenarios
├── memory-bank/             # Project documentation system
├── populate_sample_data.py  # Sample question database population
├── pyproject.toml           # Root workspace configuration
├── .gitignore              # Git ignore rules
└── README.md               # This documentation
```

## Database Models

The application uses SQLAlchemy ORM with the following core models:

- **User**: Participant information (name, role, session tracking)
- **Question**: Quiz questions with types, categories, and answers
- **Game**: Quiz session management with start/end timestamps
- **Answer**: Participant responses with correctness tracking and retry logic

### Database Features
- **Automatic Cleanup**: User and answer tables cleared on server startup
- **Session Management**: Persistent user sessions across page refreshes
- **Real-time Sync**: Live database updates via WebSocket connections
- **Performance Optimized**: Efficient queries for high-concurrency scenarios

## API Endpoints

- `GET /api/` - API root
- `GET /api/health` - Health check
- `WebSocket /ws/participant` - Participant real-time connection
- `WebSocket /ws/admin` - Quiz master real-time connection

## Admin Interface Features

### Quiz Control Panel
- **Real-time Status Dashboard**: Live participant count, quiz status, current question
- **Question Progress**: Accurate "X of Y" progress tracking with proper question counting
- **Answer Analytics**: Live answer table with timestamps, retry counts, and correctness
- **Timer Control**: 30-second countdown with visual feedback
- **Drawing Canvas**: Interactive drawing board for creative questions

### Question Management System
- **Add Questions**: Create new questions with multiple types and categories
- **Question Library**: View all questions with category badges and delete functionality
- **Category Summary**: Visual breakdown showing question counts by category (geography, science, history, general)
- **Real-time Sync**: Questions load automatically with WebSocket updates

### Reveal Answer System
- **Smart Visibility**: Reveal button only appears during active quiz sessions
- **Proper Styling**: Orange warning button that clearly indicates action availability
- **Answer Display**: Shows correct answers with options for multiple choice questions

## WebSocket Message Types

### From Server to Clients
- `quiz_started` - Quiz begins with progress info (current: 0, total: X)
- `question` - New question broadcast with progress tracking
- `question_pushed` - Question successfully pushed to participants
- `drawing_update` - Live drawing strokes from quiz master
- `timer_update` - Timer countdown updates
- `answer_revealed` - Correct answer revealed to all participants
- `quiz_ended` - Quiz finished, cleanup state
- `status_update` - Real-time dashboard updates (participant count, answers, etc.)
- `questions_loaded` - Question library data sent to admin
- `question_added` - Confirmation of new question creation
- `question_deleted` - Confirmation of question removal
- `reveal_confirmed` - Answer reveal acknowledgment

### From Clients to Server
- `join` - Participant joins with name
- `answer` - Participant answer submission with retry logic
- `start_quiz` - Quiz master starts game
- `next_question` - Push next question in sequence
- `end_quiz` - Quiz master ends session
- `add_question` - Create new question
- `delete_question` - Remove question by index
- `get_questions` - Request question library data
- `reveal_answer` - Show correct answer to participants
- `drawing_stroke` - Drawing coordinates for collaborative drawing
- `push_drawing` - Send completed drawing to participants

## Development

### Running in Development Mode
```bash
uv run python backend/main.py
```
The server supports hot reload for development.

### Debug Features
The application includes comprehensive debug logging for troubleshooting:

**Server-side Debug Logs:**
- Question loading: `Admin X requested questions`, `Found Y questions in database`
- Quiz progress: `Starting quiz with X total questions`, `Pushing question Y of X`
- WebSocket events: Connection/disconnection tracking

**Client-side Debug Logs:**
- Question management: `Loading questions...`, `Updating questions list with: [...]`
- WebSocket messages: Real-time message flow tracking
- Error handling: Graceful failure recovery with detailed error messages

**Browser Console:**
Open F12 Developer Tools → Console tab to view client-side debug output.

**Terminal Output:**
Server logs provide backend operation visibility for performance monitoring.

### Testing
The project includes comprehensive testing infrastructure for validating performance with 150 concurrent users.

#### Quick Test Commands
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov

# Run specific test categories
uv run pytest tests/unit_tests/          # Unit tests
uv run pytest tests/integration_tests/   # Integration tests
```

#### Load Testing for 150 Users
The project includes specialized load testing tools to validate performance under full user load:

##### Prerequisites for Load Testing
1. **Start the quiz server:**
   ```bash
   uv run python backend/main.py
   ```

2. **In a separate terminal, run load tests:**
   ```bash
   # Full 150-user test (requires server running)
   uv run python tests/load_tests/test_scenarios.py 150user

   # Gradual scaling test (10→50→100→150 users)
   uv run python tests/load_tests/test_scenarios.py scaling

   # Stress test with connection churn
   uv run python tests/load_tests/test_scenarios.py stress

   # Correctness validation under load
   uv run python tests/load_tests/test_scenarios.py correctness
   ```

##### Locust Web Interface (Alternative)
```bash
# Start Locust web interface
uv run locust -f tests/load_tests/locustfile.py --host http://localhost:8000

# Open http://localhost:8089 and configure:
# - Number of users: 150
# - Spawn rate: 10 users/second
# - Run for 5-10 minutes
```

#### Test Results and Reports
Load tests generate comprehensive reports including:
- **System Performance**: CPU, memory, network usage
- **Application Metrics**: WebSocket events, quiz interactions
- **Performance Scoring**: A-F grade with specific recommendations
- **Bottleneck Analysis**: Identification of scaling issues

Reports are saved as JSON files with timestamps for analysis.

#### Testing Architecture
```
tests/
├── unit_tests/           # Database models, business logic
├── integration_tests/    # WebSocket connections, HTTP endpoints
└── load_tests/           # 150-user performance validation
    ├── locustfile.py     # Locust load testing framework
    ├── monitoring.py     # System monitoring and metrics
    └── test_scenarios.py # Comprehensive test scenarios
```

#### Key Testing Features
- **Real-time WebSocket Testing**: Validates bidirectional communication
- **System Resource Monitoring**: CPU, memory, network tracking
- **Performance Scoring**: Automated assessment of system health
- **Gradual Scaling Tests**: Identifies performance degradation points
- **Stress Testing**: Connection churn and peak load simulation
- **Correctness Validation**: Ensures quiz logic accuracy under load

### Browser Compatibility
- Chrome 70+
- Firefox 65+
- Safari 12+
- Edge 79+

## Deployment

### Docker (Recommended)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY frontend/ ./static/

EXPOSE 8000
CMD ["python", "main.py"]
```

### Cloud Deployment
- **AWS**: Elastic Beanstalk or ECS
- **Google Cloud**: App Engine or Cloud Run
- **Azure**: App Service

### Production Considerations
- Use production WSGI server (gunicorn)
- Set up reverse proxy (nginx)
- Configure environment variables for secrets
- Enable HTTPS
- Set up monitoring and logging

## Contributing

1. Follow the established project structure
2. Update memory-bank documentation for significant changes
3. Test across multiple browsers
4. Ensure WebSocket connections handle network interruptions

## License

This project is part of the All-Hands Quiz Game system.

## Memory Bank

This project uses a comprehensive memory bank system for documentation:
- `memory-bank/projectbrief.md` - Project overview
- `memory-bank/productContext.md` - Business context
- `memory-bank/activeContext.md` - Current work status
- `memory-bank/systemPatterns.md` - Architecture patterns
- `memory-bank/techContext.md` - Technical details
- `memory-bank/progress.md` - Development progress

Refer to these files for detailed project information and context.
