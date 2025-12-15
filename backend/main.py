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

# --- Word Cloud Embedding/Clustering Imports ---
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

# Load the embedding model globally (MiniLM is fast and small)
WORD_CLOUD_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def cluster_word_cloud_answers(answers, similarity_threshold=0.75):
    """
    Groups similar word cloud answers using sentence-transformers.
    Args:
        answers: List of (user_id, answer_string)
        similarity_threshold: Cosine similarity threshold for grouping
    Returns:
        cluster_map: dict {cluster_id: {"users": [user_id,...], "answers": [str], "rep": str}}
        answer_to_cluster: dict {user_id: cluster_id}
    """
    if not answers:
        return {}, {}

    user_ids, answer_texts = zip(*answers)
    embeddings = WORD_CLOUD_MODEL.encode(answer_texts, convert_to_tensor=True)

    # Cosine similarity matrix
    cosine_scores = util.pytorch_cos_sim(embeddings, embeddings).cpu().numpy()

    n = len(answers)
    visited = [False] * n
    clusters = []
    for i in range(n):
        if not visited[i]:
            # Group all answers with cosine similarity >= threshold to i
            cluster = [i]
            visited[i] = True
            for j in range(i+1, n):
                if not visited[j] and cosine_scores[i,j] >= similarity_threshold:
                    cluster.append(j)
                    visited[j] = True
            clusters.append(cluster)

    cluster_map = {}
    answer_to_cluster = {}
    for idx, cluster in enumerate(clusters):
        cluster_user_ids = [user_ids[i] for i in cluster]
        cluster_answers = [answer_texts[i] for i in cluster]
        # Cluster representative: the most common answer, or first answer
        rep = max(set(cluster_answers), key=cluster_answers.count)
        cluster_map[idx] = {"users": cluster_user_ids, "answers": cluster_answers, "rep": rep}
        for user_id in cluster_user_ids:
            answer_to_cluster[user_id] = idx

    return cluster_map, answer_to_cluster

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
            try:
                await self.active_connections[connection_id].send_json(message)
            except Exception:
                # Silently ignore errors when sending to a closed connection
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]

    async def broadcast(self, message: dict, exclude_connections: Optional[set] = None):
        exclude_connections = exclude_connections or set()
        # Iterate over a copy of items to allow safe removal of broken connections
        for connection_id, connection in list(self.active_connections.items()):
            if connection_id not in exclude_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Silently ignore errors when broadcasting to a closed connection
                    if connection_id in self.active_connections:
                        del self.active_connections[connection_id]

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

# --- Wheel of Fortune state ---
wof_revealed_indices: Optional[List[bool]] = None  # Indices in current phrase that are revealed (now List[bool])
wof_reveal_task: Optional[asyncio.Task] = None   # Background tile reveal task
wof_winner: Optional[str] = None                 # Winning participant name
wof_tile_duration: float = 2.0                   # seconds per tile (could be set via admin/settings)

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
# --- Word cloud scoring tracking ---
word_cloud_scored = False

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
                debug_question_payload = {
                    "id": current_question.id,
                    "type": current_question.type,
                    "content": current_question.content,
                    # No category: always just use content for prompt
                    "options": json.loads(current_question.answers) if current_question.answers else None,
                    "allow_multiple": getattr(current_question, 'allow_multiple', True),
                }
                print("[DEBUG] SENDING QUESTION TO PARTICIPANT:", debug_question_payload)
                await participant_manager.send_personal_message({
                    "type": "question",
                    "question": debug_question_payload
                }, connection_id)

        try:
            while True:
                data = await websocket.receive_json()


                if data["type"] == "answer":
                    global word_cloud_scored, wof_winner, wof_reveal_task
                    existing = db.query(Answer).filter(
                        Answer.user_id == participant.id,
                        Answer.question_id == data["question_id"],
                        Answer.game_id == current_game.id if current_game else None
                    ).first()
                    
                    is_word_cloud = current_question and current_question.type == "word_cloud"
                    is_wof = current_question and current_question.type == "wheel_of_fortune"
                    is_correct = False
                    score = 0

                    # ---- WHEEL OF FORTUNE LOGIC ----
                    if is_wof and current_question and data["question_id"] == current_question.id and not wof_winner:
                        # Accept full phrase guess, ignore case and whitespace; don't allow partial answers
                        guess = (data["answer"] or "").strip().lower()
                        answer = (current_question.correct_answer or "").strip().lower()
                        if guess == answer:
                            is_correct = True
                            wof_winner = participant.name
                            # Kill the letter-reveal engine if still running
                            if wof_reveal_task:
                                wof_reveal_task.cancel()
                                wof_reveal_task = None
                            # Mark all tiles revealed
                            if wof_revealed_indices is not None:
                                for idx in range(len(wof_revealed_indices)):
                                    wof_revealed_indices[idx] = True
                            # Score = seconds remaining (from main timer, or max if timer is not running)
                            seconds_remaining = 30
                            if question_start_time is not None:
                                elapsed_time = asyncio.get_event_loop().time() - question_start_time
                                seconds_remaining = max(0, 30 - int(elapsed_time))
                            score = seconds_remaining

                            # Insert a new Answer or update previous (to track leaderboard as normal)
                            if existing:
                                existing.content = data["answer"]
                                existing.is_correct = True
                                existing.score = score
                                existing.retry_count += 1
                                existing.timestamp = datetime.utcnow()
                            else:
                                answer_obj = Answer(
                                    user_id=participant.id,
                                    question_id=data["question_id"],
                                    game_id=current_game.id if current_game else None,
                                    content=data["answer"],
                                    is_correct=True,
                                    score=score,
                                    retry_count=1
                                )
                                db.add(answer_obj)
                            db.commit()

                            await broadcast_wof_state(current_question.correct_answer or "", finished=True, winner=wof_winner)
                            await participant_manager.send_personal_message({
                                "type": "personal_feedback",
                                "correct": True,
                                "score": score,
                                "total_score": score,  # optionally sum, for now single-question
                                "retry_count": existing.retry_count+1 if existing else 1,
                                "allow_multiple": False
                            }, connection_id)
                            # Notify all clients that the round is done and who won
                            await admin_manager.broadcast({
                                "type": "wof_winner",
                                "winner": wof_winner,
                                "answer": current_question.correct_answer
                            })
                            await participant_manager.broadcast({
                                "type": "wof_winner",
                                "winner": wof_winner,
                                "answer": current_question.correct_answer
                            })
                            continue  # Don't do normal answer/leaderboard logic

                        # Wrong guess – feedback only
                        await participant_manager.send_personal_message({
                            "type": "personal_feedback",
                            "correct": False,
                            "score": 0,
                            "total_score": 0,
                            "retry_count": existing.retry_count+1 if existing else 1,
                            "allow_multiple": True
                        }, connection_id)
                        continue  # Do not record incorrect guesses for leaderboard (if desired)
                    # ---- END OF WOF LOGIC ----

                    # CUSTOM: For word_cloud, always accept and ignore is_correct/scoring at this stage
                    if current_question and data["question_id"] == current_question.id and not is_word_cloud:
                        is_correct = (data["answer"].strip().lower() == current_question.correct_answer.strip().lower())
                        if is_correct and question_start_time is not None:
                            elapsed_time = asyncio.get_event_loop().time() - question_start_time
                            seconds_remaining = max(0, 30 - elapsed_time)
                            score = int(seconds_remaining)  # Convert to integer seconds

                    if existing and (not existing.is_correct or is_word_cloud):
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

                    user_answers = db.query(Answer).filter(
                        Answer.user_id == participant.id,
                        Answer.game_id == current_game.id if current_game else None
                    ).all()
                    total_score = sum(ans.score for ans in user_answers)

                    # Send personal feedback to participant
                    # For word_cloud, do not mark as correct/incorrect -- just acknowledge
                    if is_word_cloud:
                        await participant_manager.send_personal_message({
                            "type": "personal_feedback",
                            "correct": False,
                            "score": 0,
                            "total_score": total_score,
                            "retry_count": existing.retry_count if existing else 1,
                            "allow_multiple": False,
                            "scoring_status": "pending"
                        }, connection_id)
                    else:
                        await participant_manager.send_personal_message({
                            "type": "personal_feedback",
                            "correct": is_correct,
                            "score": score,
                            "total_score": total_score,
                            "retry_count": existing.retry_count if existing else 1,
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

                    # --- NEW: Auto-scoring for word_cloud when all have answered ---
                    if is_word_cloud and not word_cloud_scored:
                        total_participants = participant_manager.get_participant_count()
                        submitted_count = db.query(Answer).filter(
                            Answer.question_id == current_question.id,
                            Answer.game_id == current_game.id if current_game else None
                        ).count()
                        if submitted_count >= total_participants:
                            await score_word_cloud_and_reveal(db)

        except WebSocketDisconnect:
            participant_manager.disconnect(connection_id)
            db.close()

    except Exception as e:
        print(f"Error in participant websocket: {e}")
        db.close()

ALLOWED_QUESTION_TYPES = {
    "fill_in_the_blank",
    "multiple_choice",
    "word_cloud",
    "pictionary",
    "wheel_of_fortune"
}

@app.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket):
    # Establish connection and obtain a unique connection ID
    connection_id = await admin_manager.connect(websocket, "admin")

    # If a quiz is already active, send the current timer state to the new admin
    if current_game and current_game.status == "active" and current_question:
        await admin_manager.send_personal_message(
            {"type": "timer_update", "time_left": 30},
            connection_id,
        )

    try:
        while True:
            # Receive a message from the admin client
            data = await websocket.receive_json()
            db = SessionLocal()
            try:
                # ---------- Quiz lifecycle ----------
                if data["type"] == "start_quiz":
                    await start_quiz(db)
                    await admin_manager.send_personal_message(
                        {"type": "quiz_started", "progress": {"current": 0, "total": total_questions}},
                        connection_id,
                    )
                    await participant_manager.broadcast(
                        {"type": "quiz_started", "progress": {"current": 0, "total": total_questions}}
                    )
                elif data["type"] == "next_question":
                    global word_cloud_scored
                    await next_question(db)
                    word_cloud_scored = False
                    if current_question:
                        print(f"Pushing next question ID {current_question.id} (index {current_question_index}/{total_questions})")
                        question_payload = {
                            "type": "question",
                            "question": {
                                "id": current_question.id,
                                "type": current_question.type,
                                "content": current_question.content,
                                "options": json.loads(current_question.answers) if current_question.answers else None,
                                "allow_multiple": getattr(current_question, "allow_multiple", True),
                                "correct_answer": current_question.correct_answer if current_question.type == "wheel_of_fortune" else None,
                            },
                            "progress": {"current": current_question_index, "total": total_questions},
                        }
                        await admin_manager.broadcast(
                            {"type": "question_pushed", "question": question_payload["question"], "progress": question_payload["progress"]}
                        )
                        await participant_manager.broadcast(question_payload)

                        # Start default 30s timer for all questions (admin sees 30s initially)
                        # For WoF, this gets replaced when countdown starts
                        await start_question_timer()
                elif data["type"] == "end_quiz":
                    await end_quiz(db)
                    await admin_manager.broadcast({"type": "quiz_ended"})
                    await participant_manager.broadcast({"type": "quiz_ended"})
                # ---------- Question management ----------
                elif data["type"] == "add_question":
                    qd = data["question"]
                    if qd["type"] not in ALLOWED_QUESTION_TYPES:
                        await admin_manager.send_personal_message({"type": "question_add_error", "error": f"Unknown question type '{qd['type']}'. Must be one of {sorted(ALLOWED_QUESTION_TYPES)}."}, connection_id)
                        continue
                    new_question = Question(
                        type=qd["type"],
                        content=qd["content"],
                        correct_answer=qd["correct_answer"],
                        category=qd.get("category", "general"),
                        allow_multiple=qd.get("allow_multiple", True),
                        answers=json.dumps(qd.get("options", [])) if "options" in qd else None,
                    )
                    db.add(new_question)
                    db.commit()
                    await admin_manager.send_personal_message({"type": "question_added"}, connection_id)
                elif data["type"] == "edit_question":
                    idx = data.get("index")
                    qd = data["question"]
                    if qd["type"] not in ALLOWED_QUESTION_TYPES:
                        await admin_manager.send_personal_message({"type": "question_edit_error", "error": f"Unknown question type '{qd['type']}'. Must be one of {sorted(ALLOWED_QUESTION_TYPES)}."}, connection_id)
                        continue
                    question = db.query(Question).order_by(Question.id).offset(idx).first()
                    if question:
                        question.type = qd["type"]
                        question.content = qd["content"]
                        question.correct_answer = qd["correct_answer"]
                        question.category = qd.get("category", question.category)
                        question.allow_multiple = qd.get("allow_multiple", question.allow_multiple)
                        if "options" in qd:
                            question.answers = json.dumps(qd["options"])
                        db.commit()
                        await admin_manager.send_personal_message({"type": "question_updated"}, connection_id)
                elif data["type"] == "get_questions":
                    # Sort questions by .order if present; fallback to id for legacy
                    questions = db.query(Question).order_by(getattr(Question, "order", Question.id)).all()
                    questions_payload = []
                    for q in questions:
                        parsed_answers = json.loads(q.answers) if q.answers else []
                        payload = {
                            "id": q.id,
                            "type": q.type,
                            "content": q.content,
                            "correct_answer": q.correct_answer,
                            "category": q.category,
                            "allow_multiple": q.allow_multiple,
                            "answers": parsed_answers,
                        }
                        if q.type in ("multiple_choice", "multiplechoice", "mcq"):
                            payload["options"] = parsed_answers
                        questions_payload.append(payload)
                    await admin_manager.send_personal_message(
                        {"type": "questions_loaded", "questions": questions_payload},
                        connection_id,
                    )
                # ----- REORDER QUESTIONS: new logic -----
                elif data["type"] == "reorder_questions":
                    # Data: {"order": [q1id, q2id, ...]}
                    id_list = data.get("order", [])
                    order_field_exists = hasattr(Question, "order")
                    # Only proceed if .order field exists (otherwise suggest migration)
                    if order_field_exists and id_list:
                        for idx, qid in enumerate(id_list):
                            qobj = db.query(Question).filter(Question.id == qid).first()
                            if qobj:
                                setattr(qobj, "order", idx)
                        db.commit()
                        print(f"[DEBUG] Updated question order: {id_list}")
                        await admin_manager.send_personal_message({"type": "questions_reordered"}, connection_id)
                    else:
                        print("[WARN] Question ordering failed: 'order' field missing or bad id_list.")
                        await admin_manager.send_personal_message({"type": "questions_reorder_failed"}, connection_id)
                elif data["type"] == "delete_question":
                    idx = data["index"]
                    ordered = db.query(Question).order_by(Question.id).all()
                    if 0 <= idx < len(ordered):
                        db.delete(ordered[idx])
                        db.commit()
                        await admin_manager.send_personal_message({"type": "question_deleted"}, connection_id)
                # ---------- Settings ----------
                elif data["type"] == "save_settings":
                    # Handle settings sent from admin UI (including WoF tile duration)
                    s = data["settings"]
                    global wof_tile_duration
                    if "wof_tile_duration" in s:
                        try:
                            wof_tile_duration = float(s["wof_tile_duration"])
                        except Exception:
                            print("Invalid value for wof_tile_duration, keeping previous.")
                    print(f"Settings saved: {data['settings']}, wof_tile_duration now {wof_tile_duration}")
                    await admin_manager.send_personal_message({"type": "settings_saved"}, connection_id)
                # ---------- Drawing ----------
                # Drawing updates only sent to admin (participants see via screen share)
                elif data["type"] == "drawing_stroke":
                    pass  # No longer broadcast to participants

                # ---------- Start WoF Countdown ----------
                elif data["type"] == "start_wof_countdown":
                    if current_question and current_question.type == "wheel_of_fortune":
                        # Calculate timer duration: len(answer) * tile_duration
                        answer_length = len(current_question.correct_answer or "")
                        timer_duration = int(answer_length * wof_tile_duration)
                        print(f"[WoF] Starting countdown with duration: {timer_duration}s ({answer_length} letters × {wof_tile_duration}s)")

                        # Start the reveal engine
                        wof_reveal_task = asyncio.create_task(wof_phrase_reveal_engine(current_question.correct_answer or ""))

                        # Start the timer with calculated duration
                        timer_task = asyncio.create_task(start_wof_timer(timer_duration))
                        await admin_manager.broadcast({
                            "type": "wof_countdown_started",
                            "timer_duration": timer_duration
                        })
                        await participant_manager.broadcast({
                            "type": "wof_countdown_started",
                            "timer_duration": timer_duration
                        })
                    else:
                        print("[WoF] Attempted to start countdown but no WoF question active")
                # ---------- Reveal answer ----------
                elif data["type"] == "reveal_answer":
                    if not current_question:
                        await admin_manager.send_personal_message(
                            {"type": "reveal_error", "message": "No active question"},
                            connection_id,
                        )
                        continue
                    # --- Begin word_cloud answer clustering and reveal ---
                    if current_question.type == "word_cloud":
                        await score_word_cloud_and_reveal(db, admin_connection_id=connection_id)
                    else:
                        # DEFAULT: legacy reveal behavior for non-word_cloud questions
                        reveal_payload = {
                            "type": "answer_revealed",
                            "correct_answer": current_question.correct_answer or "",
                            "question_id": current_question.id,
                            "question_type": current_question.type
                        }
                        await admin_manager.broadcast(reveal_payload)
                        await participant_manager.broadcast(reveal_payload)
                        await admin_manager.send_personal_message({"type": "reveal_confirmed"}, connection_id)
            finally:
                db.close()
    except WebSocketDisconnect:
        admin_manager.disconnect(connection_id)
    except Exception as e:
        print(f"Error in admin websocket: {e}")

# Game management functions
async def start_quiz(db):
    global current_game, current_question_index, total_questions
    # Clear all previous answers and participant scores for a fresh leaderboard
    db.query(Answer).delete()
    db.commit()

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
    global wof_revealed_indices, wof_reveal_task, wof_winner

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

    # Cancel any existing WoF letter-reveal
    if wof_reveal_task:
        wof_reveal_task.cancel()
        wof_reveal_task = None

    wof_revealed_indices = None
    wof_winner = None

    # Get full quiz order for debug
    ordered_questions = db.query(Question).order_by(getattr(Question, "order", Question.id)).all()
    print("[DEBUG] Question order for quiz play:")
    for q in ordered_questions:
        print(f"    id={q.id} order={getattr(q, 'order', 'none')} content={q.content[:40]!r}")

    # Get next question IN PERSISTED ORDER
    question = db.query(Question).order_by(getattr(Question, "order", Question.id)).offset(current_question_index).first()
    if question:
        print(f"[DEBUG] PUSHING question idx={current_question_index} id={question.id} order={getattr(question, 'order', 'none')} content={question.content[:60]!r}")
        current_question = question
        current_question_index += 1
        # Record when this question was pushed for time-based scoring
        question_start_time = asyncio.get_event_loop().time()

        # For WoF, initialize state but don't start reveal yet (wait for countdown)
        if question.type == "wheel_of_fortune":
            phrase = question.correct_answer or ""
            # Initialize revealed indices (non-letters are always revealed)
            wof_revealed_indices = [False] * len(phrase)
            for idx, c in enumerate(phrase):
                if not c.isalnum():
                    wof_revealed_indices[idx] = True
            # Don't start reveal engine yet - wait for start_wof_countdown

async def wof_phrase_reveal_engine(phrase):
    """
    This async task is started when a WoF round begins,
    revealing letters at intervals and notifying clients of current state.
    """
    global wof_revealed_indices, wof_winner

    try:
        if wof_revealed_indices is None:
            return
        while not wof_winner and not all(wof_revealed_indices):
            # Reveal the next unrevealed letter in L->R order
            for idx, flag in enumerate(wof_revealed_indices):
                if not flag:
                    wof_revealed_indices[idx] = True
                    break

            await broadcast_wof_state(phrase)
            # If puzzle is now complete with no winner, broadcast solution/end
            if all(wof_revealed_indices):
                await broadcast_wof_state(phrase, finished=True)
                break
            await asyncio.sleep(wof_tile_duration)
    except asyncio.CancelledError:
        # Clean up if question is skipped/canceled
        pass

async def broadcast_wof_state(phrase, finished=False, winner=None):
    """
    Broadcasts masked phrase board, revealed indices, and winner to admin only.
    Participants see the board via screen share.
    """
    board = ""
    if wof_revealed_indices is not None:
        board = "".join(c if revealed else "_" for c, revealed in zip(phrase, wof_revealed_indices))
    # Only send to admin - participants see via screen share
    await admin_manager.broadcast({
        "type": "wof_update",
        "board": board,
        "revealed_indices": wof_revealed_indices,
        "winner": winner,
        "finished": finished
    })

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
        global word_cloud_scored
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
        # Timer expired
        await admin_manager.broadcast({
            "type": "time_expired"
        })
        # --- Auto-score word_cloud on expiry ---
        if current_question and current_question.type == "word_cloud" and not word_cloud_scored:
            db = SessionLocal()
            try:
                await score_word_cloud_and_reveal(db)
            finally:
                db.close()

    question_timer = asyncio.create_task(timer_task())

async def start_wof_timer(duration):
    """Start a WoF timer with the specified duration in seconds"""
    global question_timer

    async def timer_task():
        time_left = duration
        # Send initial timer state
        await participant_manager.broadcast({
            "type": "timer_update",
            "time_left": time_left
        })
        await admin_manager.broadcast({
            "type": "timer_update",
            "time_left": time_left
        })

        # Count down
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
        # Timer expired
        await admin_manager.broadcast({
            "type": "time_expired"
        })

    question_timer = asyncio.create_task(timer_task())

async def get_current_answers(db):
    if not current_question or not getattr(current_question, "id", None):
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
    if not current_game or not getattr(current_game, "id", None):
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

# Helper to do word cloud scoring and reveal, idempotent
async def score_word_cloud_and_reveal(db, admin_connection_id=None):
    global word_cloud_scored
    if word_cloud_scored:
        return
    word_cloud_scored = True
    # Fetch all answers
    answer_objs = []
    if current_question and getattr(current_question, "id", None) and current_game and getattr(current_game, "id", None):
        answer_objs = db.query(Answer).filter(
            Answer.question_id == current_question.id,
            Answer.game_id == current_game.id
        ).all()
    answers = [(ans.user_id, ans.content.strip()) for ans in answer_objs if ans.content and ans.content.strip()]

    cluster_map, answer_to_cluster = cluster_word_cloud_answers(answers)
    total_participants = len(answers)
    for ans in answer_objs:
        cluster_id = answer_to_cluster.get(ans.user_id)
        cluster_size = len(cluster_map[cluster_id]["users"]) if cluster_id is not None else 1
        ans.score = int(round(30 * (cluster_size / total_participants))) if total_participants > 0 else 0
        ans.is_correct = False
    db.commit()
    # Prepare for admin word cloud
    word_cloud = [
        {
            "text": cluster["rep"],
            "size": len(cluster["users"]),
            "answers": cluster["answers"]
        }
        for cluster in cluster_map.values()
    ]
    for ans in answer_objs:
        cluster_id = answer_to_cluster.get(ans.user_id)
        cluster_size = len(cluster_map[cluster_id]["users"]) if cluster_id is not None else 1
        await participant_manager.send_personal_message(
            {
                "type": "personal_feedback",
                "correct": False,
                "score": ans.score,
                "total_score": sum(a.score for a in db.query(Answer).filter(Answer.user_id == ans.user_id, Answer.game_id == current_game.id).all()),
                "retry_count": ans.retry_count,
                "allow_multiple": False,
                "cluster_size": cluster_size,
                "cluster_rep": cluster_map[cluster_id]["rep"] if cluster_id is not None else ans.content,
                "scoring_status": "complete"
            },
            ans.user.session_id
        )
    # Broadcast word cloud to admin only
    reveal_payload = {
        "type": "word_cloud_revealed",
        "question_id": current_question.id,
        "word_cloud": word_cloud,
    }
    await admin_manager.broadcast(reveal_payload)
    if admin_connection_id:
        await admin_manager.send_personal_message({"type": "reveal_confirmed"}, admin_connection_id)
    await participant_manager.broadcast(
        {"type": "word_cloud_scoring_complete", "question_id": current_question.id}
    )

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
