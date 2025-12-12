from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import WebSocket, WebSocketDisconnect
import uvicorn
import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from pathlib import Path

from models import SessionLocal, User, Question, Game, Answer

# Connection managers
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # websocket_id -> user_id

    async def connect(self, websocket: WebSocket, user_type: str, user_id: Optional[str] = None):
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket

        if user_id:
            self.user_sessions[connection_id] = user_id

        print(f"New {user_type} connection: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.user_sessions:
            del self.user_sessions[connection_id]
        print(f"Connection disconnected: {connection_id}")

    async def send_personal_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(message)

    async def broadcast(self, message: dict, exclude_connections: Optional[set] = None):
        exclude_connections = exclude_connections or set()
        for connection_id, connection in self.active_connections.items():
            if connection_id not in exclude_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to {connection_id}: {e}")

    def get_participant_count(self):
        return len(self.active_connections)

# Global connection managers
participant_manager = ConnectionManager()
admin_manager = ConnectionManager()

# Game state
current_game: Optional[Game] = None
current_question: Optional[Question] = None
current_question_index: int = 0
total_questions: int = 0
question_timer: Optional[asyncio.Task] = None
question_start_time: Optional[float] = None  # Timestamp when current question was pushed

async def cleanup_database():
    """Clean up users and answers tables at startup for fresh sessions"""
    db = SessionLocal()
    try:
        # Clear users and answers tables
        db.query(Answer).delete()
        db.query(User).delete()
        db.commit()
        print("Database cleaned: users and answers tables cleared")
    except Exception as e:
        print(f"Error cleaning database: {e}")
        db.rollback()
    finally:
        db.close()

# Lifespan event handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clean database and start background status updates
    await cleanup_database()
    status_task = asyncio.create_task(send_admin_status_updates())
    yield
    # Shutdown: Cancel background task
    status_task.cancel()
    try:
        await status_task
    except asyncio.CancelledError:
        pass

# Update FastAPI app with lifespan
app = FastAPI(title="All-Hands Quiz Game", version="0.1.0", lifespan=lifespan)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend assets (CSS, JS)
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/assets", StaticFiles(directory=str(frontend_dir)), name="assets")

# API routes under /api/
@app.get("/api/")
async def root():
    """Root API endpoint"""
    return {"message": "All-Hands Quiz Game API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Debug route
@app.get("/debug")
async def debug():
    """Debug endpoint"""
    return {"working": True}

# Serve HTML pages at root level
@app.get("/")
async def participant_page():
    """Serve participant page"""
    return FileResponse("frontend/index.html")

@app.get("/admin")
async def admin_page():
    """Serve admin page"""
    return FileResponse("frontend/admin.html")

# WebSocket endpoints
@app.websocket("/ws/participant")
async def participant_websocket(websocket: WebSocket):
    # Accept the WebSocket connection and get connection ID
    connection_id = await participant_manager.connect(websocket, "participant")

    # THEN wait for initial join message with participant name
    try:
        initial_data = await websocket.receive_json()
        if initial_data.get("type") != "join":
            await websocket.close(code=4000, reason="Expected join message")
            return

        participant_name = initial_data.get("name", "").strip()
        if not participant_name:
            await websocket.close(code=4000, result="Name is required")
            return

    except Exception as e:
        print(f"Error receiving join message: {e}")
        return

    # Create or get user session
    db = SessionLocal()
    try:
        # Create a participant user
        participant = User(
            name=participant_name,
            role="participant",
            session_id=connection_id
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)

        # Send current game state if quiz is active
        if current_game and current_game.status == "active":
            await participant_manager.send_personal_message({
                "type": "quiz_started",
                "progress": {
                    "current": current_question_index if current_question else 0,
                    "total": total_questions
                }
            }, connection_id)

            if current_question:
                await participant_manager.send_personal_message({
                    "type": "question",
                    "question": {
                        "id": current_question.id,
                        "type": current_question.type,
                        "content": current_question.content,
                        "options": json.loads(current_question.answers) if current_question.answers else None,
                        "allow_multiple": getattr(current_question, 'allow_multiple', True)
                    }
                }, connection_id)

        try:
            while True:
                data = await websocket.receive_json()

                if data["type"] == "answer":
                    # Check if user has existing answer for this question
                    existing = db.query(Answer).filter(
                        Answer.user_id == participant.id,
                        Answer.question_id == data["question_id"],
                        Answer.game_id == current_game.id if current_game else None
                    ).first()

                    # Check if correct
                    is_correct = False
                    score = 0
                    if current_question and data["question_id"] == current_question.id:
                        is_correct = (data["answer"].strip().lower() == current_question.correct_answer.strip().lower())

                        # Calculate time-based score: seconds remaining if correct, 0 if wrong
                        if is_correct and question_start_time is not None:
                            elapsed_time = asyncio.get_event_loop().time() - question_start_time
                            seconds_remaining = max(0, 30 - elapsed_time)
                            score = int(seconds_remaining)  # Convert to integer seconds

                    if existing and not existing.is_correct:
                        # Update existing answer
                        existing.content = data["answer"]
                        existing.is_correct = is_correct
                        existing.score = score
                        existing.retry_count += 1
                        existing.timestamp = datetime.utcnow()
                    else:
                        # Insert new answer
                        answer = Answer(
                            user_id=participant.id,
                            question_id=data["question_id"],
                            game_id=current_game.id if current_game else None,
                            content=data["answer"],
                            is_correct=is_correct,
                            score=score,
                            retry_count=1
                        )
                        db.add(answer)

                    db.commit()

                    # Calculate cumulative score for this user
                    user_answers = db.query(Answer).filter(
                        Answer.user_id == participant.id,
                        Answer.game_id == current_game.id if current_game else None
                    ).all()
                    total_score = sum(ans.score for ans in user_answers)

                    # Send personal feedback to participant
                    await participant_manager.send_personal_message({
                        "type": "personal_feedback",
                        "correct": is_correct,
                        "score": score,
                        "total_score": total_score,
                        "retry_count": answer.retry_count,
                        "allow_multiple": current_question.allow_multiple if current_question else True
                    }, connection_id)

                    # Notify admin of updated answers
                    answers, _ = await get_current_answers(db)
                    leaderboard = await get_cumulative_scores(db)
                    await admin_manager.broadcast({
                        "type": "answer_received",
                        "answers": answers,
                        "leaderboard": leaderboard
                    })

        except WebSocketDisconnect:
            participant_manager.disconnect(connection_id)
            db.close()

    except Exception as e:
        print(f"Error in participant websocket: {e}")
        db.close()

@app.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket):
    connection_id = await admin_manager.connect(websocket, "admin")

    # Send current timer state if quiz is active
    if current_game and current_game.status == "active" and current_question:
        # Send current timer state (assume 30 seconds for new admin connections)
        await admin_manager.send_personal_message({
            "type": "timer_update",
            "time_left": 30
        }, connection_id)

    try:
        while True:
            data = await websocket.receive_json()
            db = SessionLocal()

            try:
                if data["type"] == "start_quiz":
                    await start_quiz(db)
                    # Send initial progress info with quiz started
                    await admin_manager.send_personal_message({
                        "type": "quiz_started",
                        "progress": {
                            "current": 0,
                            "total": total_questions
                        }
                    }, connection_id)
                    await participant_manager.broadcast({
                        "type": "quiz_started",
                        "progress": {
                            "current": 0,
                            "total": total_questions
                        }
                    })

                elif data["type"] == "next_question":
                    await next_question(db)
                    if current_question:
                        question_data = {
                            "type": "question",
                            "question": {
                                "id": current_question.id,
                                "type": current_question.type,
                                "content": current_question.content,
                                "options": json.loads(current_question.answers) if current_question.answers else None,
                                "allow_multiple": getattr(current_question, 'allow_multiple', True)
                            },
                            "progress": {
                                "current": current_question_index,
                                "total": total_questions
                            }
                        }
                        print(f"Pushing question {current_question_index} of {total_questions}")
                        await admin_manager.broadcast({"type": "question_pushed", "question": question_data["question"], "progress": question_data["progress"]})
                        await participant_manager.broadcast(question_data)

                        # Start timer
                        await start_question_timer()

                elif data["type"] == "end_quiz":
                    await end_quiz(db)
                    await admin_manager.broadcast({"type": "quiz_ended"})
                    await participant_manager.broadcast({"type": "quiz_ended"})

                elif data["type"] == "add_question":
                    question_data = data["question"]
                    question = Question(
                        type=question_data["type"],
                        content=question_data["content"],
                        correct_answer=question_data["correct_answer"],
                        category=question_data.get("category", "general"),
                        allow_multiple=question_data.get("allow_multiple", True),
                        answers=json.dumps(question_data.get("options", [])) if "options" in question_data else None
                    )
                    db.add(question)
                    db.commit()

                    # Notify admin that question was added
                    await admin_manager.send_personal_message({
                        "type": "question_added"
                    }, connection_id)

                elif data["type"] == "get_questions":
                    print(f"Admin {connection_id} requested questions")
                    questions = db.query(Question).all()
                    print(f"Found {len(questions)} questions in database")
                    questions_data = [{
                        "id": q.id,
                        "type": q.type,
                        "content": q.content,
                        "correct_answer": q.correct_answer,
                        "category": q.category,
                        "allow_multiple": q.allow_multiple
                    } for q in questions]

                    print(f"Sending {len(questions_data)} questions to admin")
                    await admin_manager.send_personal_message({
                        "type": "questions_loaded",
                        "questions": questions_data
                    }, connection_id)

                elif data["type"] == "delete_question":
                    question_index = data["index"]
                    # Get all questions ordered by ID
                    questions = db.query(Question).order_by(Question.id).all()
                    if 0 <= question_index < len(questions):
                        question_to_delete = questions[question_index]
                        db.delete(question_to_delete)
                        db.commit()

                        # Notify admin that question was deleted
                        await admin_manager.send_personal_message({
                            "type": "question_deleted"
                        }, connection_id)

                elif data["type"] == "save_settings":
                    # For now, just acknowledge the settings save
                    # In a real implementation, you'd save these to database/config
                    settings = data["settings"]
                    print(f"Settings saved: {settings}")

                    await admin_manager.send_personal_message({
                        "type": "settings_saved"
                    }, connection_id)

                elif data["type"] == "drawing_stroke":
                    await participant_manager.broadcast({
                        "type": "drawing_update",
                        "stroke": data["stroke"]
                    })

                elif data["type"] == "reveal_answer":
                    if current_question:
                        reveal_data = {
                            "type": "answer_revealed",
                            "correct_answer": current_question.correct_answer,
                            "question_id": current_question.id,
                            "question_type": current_question.type,
                            "options": json.loads(current_question.answers) if current_question.answers else None
                        }
                        await admin_manager.broadcast(reveal_data)
                        await participant_manager.broadcast(reveal_data)
                        # Optionally send confirmation back to admin
                        await admin_manager.send_personal_message({
                            "type": "reveal_confirmed"
                        }, connection_id)
                    else:
                        await admin_manager.send_personal_message({
                            "type": "reveal_error",
                            "message": "No active question"
                        }, connection_id)

            finally:
                db.close()

    except WebSocketDisconnect:
        admin_manager.disconnect(connection_id)
    except Exception as e:
        print(f"Error in admin websocket: {e}")

# Game management functions
async def start_quiz(db):
    global current_game, current_question_index, total_questions
    current_game = Game(status="active")
    db.add(current_game)
    db.commit()
    db.refresh(current_game)

    # Initialize question progress
    total_questions = db.query(Question).count()
    print(f"Starting quiz with {total_questions} total questions")
    current_question_index = 0

async def next_question(db):
    global current_question, question_timer, current_question_index, question_start_time

    # Only allow next question if quiz is active and not exhausted
    if not current_game or current_game.status != "active":
        print("Cannot push next question - quiz not active")
        return

    total = db.query(Question).count()
    if current_question_index >= total:
        print("No more questions to push")
        return

    # Cancel existing timer
    if question_timer:
        question_timer.cancel()
        # Notify admin to reset the timer value immediately (force admin timer to 30)
        await admin_manager.broadcast({
            "type": "timer_update",
            "time_left": 30
        })

    # Get next question
    question = db.query(Question).offset(current_question_index).first()
    if question:
        current_question = question
        current_question_index += 1
        # Record when this question was pushed for time-based scoring
        question_start_time = asyncio.get_event_loop().time()

async def end_quiz(db):
    global current_game, current_question, question_timer

    if current_game:
        current_game.status = "finished"
        current_game.finished_at = datetime.utcnow()
        db.commit()

    current_game = None
    current_question = None

    if question_timer:
        question_timer.cancel()
        question_timer = None

async def start_question_timer():
    global question_timer

    async def timer_task():
        time_left = 30
        # Send initial timer state (30 seconds)
        await participant_manager.broadcast({
            "type": "timer_update",
            "time_left": time_left
        })
        await admin_manager.broadcast({
            "type": "timer_update",
            "time_left": time_left
        })

        # Count down from 29 to 0
        while time_left > 0:
            await asyncio.sleep(1)
            time_left -= 1
            # Send timer updates to both participants and admins
            await participant_manager.broadcast({
                "type": "timer_update",
                "time_left": time_left
            })
            await admin_manager.broadcast({
                "type": "timer_update",
                "time_left": time_left
            })
        # Timer expired, notify admin
        await admin_manager.broadcast({
            "type": "time_expired"
        })

    question_timer = asyncio.create_task(timer_task())

async def get_current_answers(db):
    if not current_question:
        return [], 0

    answers = db.query(Answer, User).join(User).filter(
        Answer.question_id == current_question.id
    ).all()

    correct_count = sum(1 for answer, _ in answers if answer.is_correct)

    # Sort answers by score (descending) for ranking
    answer_data = [{
        "user": user.name,
        "content": answer.content,
        "correct": answer.is_correct,
        "score": answer.score,
        "retry_count": answer.retry_count,
        "timestamp": answer.timestamp.isoformat() if answer.timestamp else None
    } for answer, user in answers]

    # Sort by score descending for question rankings
    answer_data.sort(key=lambda x: x["score"], reverse=True)

    return answer_data, correct_count

async def get_cumulative_scores(db):
    """Get cumulative scores for all users in the current game"""
    if not current_game:
        return []

    # Get all answers for the current game
    answers = db.query(Answer, User).join(User).filter(
        Answer.game_id == current_game.id
    ).all()

    # Aggregate scores by user
    user_scores = {}
    for answer, user in answers:
        user_id = user.id
        if user_id not in user_scores:
            user_scores[user_id] = {
                "user_id": user_id,
                "user_name": user.name,
                "total_score": 0,
                "questions_answered": 0,
                "correct_answers": 0
            }
        user_scores[user_id]["total_score"] += answer.score
        user_scores[user_id]["questions_answered"] += 1
        if answer.is_correct:
            user_scores[user_id]["correct_answers"] += 1

    # Convert to list and sort by total score descending
    leaderboard = list(user_scores.values())
    leaderboard.sort(key=lambda x: x["total_score"], reverse=True)

    return leaderboard

# Periodic status updates for admin
async def send_admin_status_updates():
    while True:
        try:
            db = SessionLocal()
            try:
                answers, correct_count = await get_current_answers(db)
                leaderboard = await get_cumulative_scores(db)
                total_answered = len(answers)
                # Send participant count, quiz status, total answered, correct answer count, and leaderboard
                status_update = {
                    "type": "status_update",
                    "participant_count": participant_manager.get_participant_count(),
                    "quiz_active": current_game is not None and current_game.status == "active",
                    "current_question": current_question.content if current_question else None,
                    "question_type": current_question.type if current_question else None,
                    "total_answered": total_answered,
                    "correct_answers": correct_count,
                    "leaderboard": leaderboard
                }

                await admin_manager.broadcast(status_update)
            finally:
                db.close()
        except Exception as e:
            print(f"Error sending status update: {e}")

        await asyncio.sleep(2)  # Update every 2 seconds

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
