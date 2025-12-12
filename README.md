# All-Hands Quiz Game 🎄

An interactive real-time quiz game for Zoom all-hands meetings with up to 150 participants. Features multiple question types, live drawing, voice input, and Christmas-themed UI.

## Features

- **Multiple Question Types**: Fill-in-the-blank, word cloud, live drawing, wheel of fortune, multiple choice
- **Real-time Interaction**: WebSocket-based communication for instant responses
- **Voice Input**: Browser-native speech-to-text support
- **Live Drawing**: Real-time collaborative drawing for quiz master
- **Christmas Theme**: Festive UI with subtle holiday styling
- **Scalable**: Supports up to 150 concurrent participants
- **Admin Panel**: Password-protected quiz master controls

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
2. **For Quiz Master**: Open http://localhost:8000/admin and login with password `quizzer`

### During Zoom Meeting

1. Quiz master shares their screen showing the admin panel
2. Participants join via the participant page URL
3. Quiz master adds questions and controls the game flow
4. Real-time answers and scores are displayed

## Project Structure

```
all-hands-game/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── models.py            # Database models
│   └── pyproject.toml       # Backend package configuration
├── frontend/
│   ├── index.html           # Participant page
│   ├── admin.html           # Quiz master page
│   ├── styles.css           # Christmas-themed styles
│   ├── app.js               # Participant client logic
│   └── admin.js             # Quiz master client logic
├── memory-bank/             # Project documentation
├── tests/                   # Comprehensive testing suite
├── populate_sample_data.py  # Database population script
├── pyproject.toml           # Root workspace configuration
└── README.md               # This file
```

## API Endpoints

- `GET /api/` - API root
- `GET /api/health` - Health check
- `WebSocket /ws/participant` - Participant real-time connection
- `WebSocket /ws/admin` - Quiz master real-time connection

## WebSocket Message Types

### From Server to Clients
- `quiz_started` - Quiz begins
- `question` - New question broadcast
- `drawing_start` - Drawing mode activated
- `drawing_update` - Live drawing strokes
- `timer_update` - Timer countdown
- `quiz_ended` - Quiz finished

### From Clients to Server
- `answer` - Participant answer submission
- `start_quiz` - Quiz master starts game
- `next_question` - Push next question
- `add_question` - Add new question
- `drawing_stroke` - Drawing coordinates

## Development

### Running in Development Mode
```bash
uv run python backend/main.py
```
The server supports hot reload for development.

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
