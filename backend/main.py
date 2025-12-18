from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import WebSocket, WebSocketDisconnect
import uvicorn
import os
import json
import asyncio
import hashlib
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from pathlib import Path
import argparse
import yaml

from models import SessionLocal, User, Question, Game, Answer, switch_database, SQLALCHEMY_DATABASE_URL

from collections import Counter, defaultdict

# --- Word Cloud Embedding/Clustering Imports ---
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from word2number import w2n

# Load the embedding model globally (MiniLM is fast and small)
WORD_CLOUD_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

# Settings management
SETTINGS_FILE = Path(__file__).parent / "settings.yaml"

def load_settings():
    """Load settings from YAML file"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

def save_settings(settings):
    """Save settings to YAML file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            yaml.dump(settings, f, default_flow_style=False)
        print("Settings saved to", SETTINGS_FILE)
    except Exception as e:
        print(f"Error saving settings: {e}")

# Load initial settings
SETTINGS = load_settings()

def compute_numeric_score(correct_str: str, user_str: str, max_score: int = 30) -> int:
    """Compute score for numeric fill_in_the_blank based on exact match or closeness ranking."""
    try:
        correct_num = extract_number_from_text(correct_str)
        if correct_num is None:
            return 0

        user_num = extract_number_from_text(user_str)
        if user_num is None:
            return 0  # Couldn't extract a number from user input

        # Exact match always gets full points
        if user_num == correct_num:
            return max_score

        # For non-exact matches, this will be called later for ranking
        # Return a small score based on closeness for now (will be adjusted by ranking)
        diff = abs(user_num - correct_num)
        # Return inverse of difference (closer = higher score, but not full)
        # This will be used for initial ranking, then adjusted proportionally
        closeness_score = max(1, int(max_score / (diff + 1)))
        return min(closeness_score, max_score - 1)  # Never full points for non-exact
    except Exception:
        return 0

def compute_top10_proportional_scores(db, question_id, game_id, correct_answer):
    """
    Compute proportional scores for the top 10 closest non-exact answers.
    All exact matches get 30 points regardless of timing.
    """
    try:
        correct_num = extract_number_from_text(correct_answer)
        if correct_num is None:
            return

        # Get all answers for this question that are not exact matches
        answers = db.query(Answer).filter(
            Answer.question_id == question_id,
            Answer.game_id == game_id
        ).all()

        non_exact_answers = []
        exact_answer_ids = []

        for ans in answers:
            user_num = extract_number_from_text(ans.content)
            if user_num is None:
                continue
            if user_num == correct_num:
                # Exact match - ensure it gets 30 points
                ans.score = 30
                ans.is_correct = True
                exact_answer_ids.append(ans.id)
            else:
                # Non-exact - calculate difference for ranking
                diff = abs(user_num - correct_num)
                non_exact_answers.append((ans, diff))

        # Sort non-exact answers by difference (closest first)
        non_exact_answers.sort(key=lambda x: x[1])

        # Take top 10 closest
        top_10 = non_exact_answers[:10]

        if not top_10:
            return

        # Assign proportional scores to top 10
        # Closer answers get higher proportional scores
        max_diff = max(diff for _, diff in top_10) if top_10 else 1

        for i, (ans, diff) in enumerate(top_10):
            if max_diff == 0:
                proportional_score = 25  # All equally close
            else:
                # Closer (smaller diff) gets higher score
                closeness_ratio = 1 - (diff / max_diff)
                proportional_score = int(25 * closeness_ratio) + 1  # 1-25 points

            ans.score = proportional_score
            ans.is_correct = False

        # Set score = 0 for all other non-exact answers (not in top 10)
        top_10_ids = {ans.id for ans, _ in top_10}
        for ans, _ in non_exact_answers:
            if ans.id not in top_10_ids:
                ans.score = 0
                ans.is_correct = False

        db.commit()

    except Exception as e:
        print(f"Error computing top 10 proportional scores: {e}")

def extract_number_from_text(text: str) -> float:
    """Extract numerical value from text containing written numbers or digits."""
    if not text or not text.strip():
        return None

    text = text.strip().lower()

    # First try direct float conversion (for "1500", "75.5", etc.)
    try:
        return float(text)
    except ValueError:
        pass

    # Try word-to-number conversion
    try:
        # Handle phrases like "eight days" -> extract "eight"
        words = text.split()
        for word in words:
            try:
                return float(w2n.word_to_num(word))
            except ValueError:
                continue

        # Try the whole phrase
        return float(w2n.word_to_num(text))
    except:
        return None

def compute_semantic_score(correct_str: str, user_str: str, max_score: int = 30, threshold: float = 0.7) -> tuple[int, float]:
    """Compute semantic similarity score for pictionary using cosine sim."""
    if not user_str.strip() or not correct_str.strip():
        return 0, 0.0

    try:
        emb1 = WORD_CLOUD_MODEL.encode([user_str.strip()])
        emb2 = WORD_CLOUD_MODEL.encode([correct_str.strip()])
        sim = util.pytorch_cos_sim(emb1, emb2).item()
        score = int(max_score * sim) if sim >= threshold else 0
        return score, sim
    except Exception:
        return 0, 0.0

def cluster_word_cloud_answers(answers, similarity_threshold=0.7):
    """
    Groups similar word cloud answers using sentence-transformers with Counter for rep.
    Args:
        answers: List of (user_id, answer_string)
        similarity_threshold: Cosine similarity threshold for grouping (lowered to 0.7)
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
        # Better rep with Counter
        rep_counter = Counter(cluster_answers)
        rep = rep_counter.most_common(1)[0][0]
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
wof_tile_duration: float = SETTINGS.get('wof_tile_duration', 2.0)  # seconds per tile (loaded from settings)

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

# Set up Jinja2 templates
templates = Jinja2Templates(directory=str(frontend_dir))

# API routes under /api/
@app.get("/api/")
async def root():
    """Root API endpoint"""
    return {"message": "All-Hands Quiz Game API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Question Import/Export API Endpoints
@app.post("/api/questions/export")
async def export_questions_api():
    """Export all questions to JSON format"""
    try:
        db = SessionLocal()
        questions = db.query(Question).order_by(Question.created_at).all()

        export_data = []
        for question in questions:
            question_data = {
                "id": question.id,
                "type": question.type,
                "content": question.content,
                "correct_answer": question.correct_answer,
                "allow_multiple": question.allow_multiple,
                "order": getattr(question, 'order', 0),
                "created_at": question.created_at.isoformat() if question.created_at else None
            }

            # Only include answers for question types that use them
            if question.type in ["multiple_choice", "multiplechoice", "mcq"]:
                if question.answers:
                    try:
                        question_data["answers"] = json.loads(question.answers)
                    except json.JSONDecodeError:
                        question_data["answers"] = []

            export_data.append(question_data)

        return {
            "success": True,
            "questions": export_data,
            "count": len(export_data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/questions/import")
async def import_questions_api(request: dict):
    """Import questions from JSON data"""
    try:
        import_data = request.get("questions", [])
        if not isinstance(import_data, list):
            return {"success": False, "error": "Questions must be provided as a list"}

        drop_existing = request.get("drop_existing", False)
        skip_duplicates = request.get("skip_duplicates", True)
        update_existing = request.get("update_existing", False)

        db = SessionLocal()
        imported = 0
        skipped = 0
        updated = 0
        dropped = 0

        # Drop existing questions if requested
        if drop_existing:
            existing_count = db.query(Question).count()
            if existing_count > 0:
                db.query(Question).delete()
                db.commit()
                dropped = existing_count

        def calculate_question_hash(question_data):
            """Calculate hash for deduplication"""
            hash_content = f"{question_data['type']}|{question_data['content']}|{question_data['correct_answer']}"
            if question_data.get("answers"):
                hash_content += f"|{'|'.join(sorted(question_data['answers']))}"
            return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()

        # Get existing questions for duplicate checking (only if not dropping all)
        existing_hashes = {}
        if not drop_existing and (skip_duplicates or update_existing):
            existing_questions = db.query(Question).all()
            for eq in existing_questions:
                hash_data = {
                    "type": eq.type,
                    "content": eq.content,
                    "correct_answer": eq.correct_answer,
                    "answers": json.loads(eq.answers) if eq.answers else None
                }
                existing_hashes[calculate_question_hash(hash_data)] = eq

        for question_data in import_data:
            # Basic validation
            required_fields = ["type", "content", "correct_answer"]
            if not all(field in question_data and question_data[field] for field in required_fields):
                continue

            if question_data["type"] not in ALLOWED_QUESTION_TYPES:
                continue

            question_hash = calculate_question_hash(question_data)

            # Check for existing question
            existing_question = existing_hashes.get(question_hash)
            if existing_question and not drop_existing:
                if skip_duplicates and not update_existing:
                    skipped += 1
                    continue
                elif update_existing:
                    # Update existing question
                    existing_question.type = question_data["type"]
                    existing_question.content = question_data["content"]
                    existing_question.correct_answer = question_data["correct_answer"]
                    existing_question.allow_multiple = question_data.get("allow_multiple", True)

                    if question_data["type"] in ["multiple_choice", "multiplechoice", "mcq"]:
                        existing_question.answers = json.dumps(question_data["answers"])
                    else:
                        existing_question.answers = None

                    updated += 1
                    continue

            # Create new question
            new_question = Question(
                type=question_data["type"],
                content=question_data["content"],
                correct_answer=question_data["correct_answer"],
                allow_multiple=question_data.get("allow_multiple", True),
                answers=json.dumps(question_data["answers"]) if question_data.get("answers") else None,
                order=question_data.get("order", db.query(Question).count())
            )

            db.add(new_question)
            imported += 1

        db.commit()

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "updated": updated,
            "dropped": dropped,
            "total": db.query(Question).count()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Debug route
@app.get("/debug")
async def debug():
    """Debug endpoint"""
    return {"working": True}

@app.get("/api/databases")
async def list_databases():
    """List available database files in the database folder"""
    try:
        # Debug: Show current working directory and paths
        import os
        cwd = os.getcwd()
        print(f"[DEBUG] Current working directory: {cwd}")

        db_dir = Path("./database")
        print(f"[DEBUG] Checking database directory: {db_dir.absolute()}")
        print(f"[DEBUG] Database directory exists: {db_dir.exists()}")

        if not db_dir.exists():
            print("[DEBUG] Database directory not found")
            return {"databases": []}

        # Get all .db files in the database directory
        db_files = []
        db_file_paths = list(db_dir.glob("*.db"))
        print(f"[DEBUG] Found {len(db_file_paths)} .db files: {[str(p) for p in db_file_paths]}")

        for file_path in db_file_paths:
            if file_path.is_file():
                size = file_path.stat().st_size
                print(f"[DEBUG] File: {file_path.name}, Size: {size} bytes")
                db_files.append({
                    "filename": file_path.name,
                    "path": f"database/{file_path.name}",
                    "size": size
                })

        # Sort by filename
        db_files.sort(key=lambda x: x["filename"])
        print(f"[DEBUG] Returning {len(db_files)} database files")
        return {"databases": db_files}
    except Exception as e:
        import traceback
        print(f"[DEBUG] Error in list_databases: {e}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return {"error": str(e), "databases": []}

# Serve HTML pages at root level
@app.get("/")
async def participant_page(request: Request):
    """Serve participant page"""
    scope_root_path = request.scope.get("root_path", "")
    app_root_path = request.app.root_path
    print(f"[DEBUG] Participant page - scope root_path: '{scope_root_path}', app root_path: '{app_root_path}'")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "root_path": scope_root_path}
    )

@app.get("/admin")
async def admin_page(request: Request):
    """Serve admin page"""
    scope_root_path = request.scope.get("root_path", "")
    app_root_path = request.app.root_path
    print(f"[DEBUG] Admin page - scope root_path: '{scope_root_path}', app root_path: '{app_root_path}'")
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "root_path": scope_root_path}
    )

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
                await participant_manager.send_personal_message({
                    "type": "question",
                    "question": {
                        "id": current_question.id,
                        "type": current_question.type,
                        "content": current_question.content,
                        # No category: always just use content for prompt
                        "options": json.loads(current_question.answers) if current_question.answers else None,
                        "allow_multiple": getattr(current_question, 'allow_multiple', True),
                    }
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
                    if is_wof and current_question and data["question_id"] == current_question.id:
                        # Move winner guard ABOVE all update/insert logic!
                        if wof_winner and participant.name == wof_winner:
                            # Never update, score, or write further answers for winner
                            return

                        # Accept full phrase guess, ignore case and whitespace; don't allow partial answers
                        guess = (data["answer"] or "").strip().lower()
                        answer = (current_question.correct_answer or "").strip().lower()
                        is_correct = (guess == answer)

                        if is_correct and not wof_winner:
                            wof_winner = participant.name
                            # Do NOT stop the tile-reveal engine: allow it to run to completion, so others can see the tiles reveal and play along
                            # (wof_reveal_task continues running)
                            # Do NOT reveal all tiles at this point: let the board continue revealing gradually, or finish naturally on timer, not instantly

                        # Always record the answer for live results display
                        # Score = seconds remaining for correct answers, 0 for incorrect
                        if is_correct:
                            seconds_remaining = 30
                            if question_start_time is not None:
                                elapsed_time = asyncio.get_event_loop().time() - question_start_time
                                seconds_remaining = max(0, 30 - int(elapsed_time))
                            score = seconds_remaining
                        else:
                            score = 0

                        # Insert a new Answer or update previous
                        if existing:
                            existing.content = data["answer"]
                            existing.is_correct = is_correct
                            existing.score = score
                            existing.retry_count += 1
                            existing.timestamp = datetime.utcnow()
                        else:
                            answer_obj = Answer(
                                user_id=participant.id,
                                question_id=data["question_id"],
                                game_id=current_game.id if current_game else None,
                                content=data["answer"],
                                is_correct=is_correct,
                                score=score,
                                retry_count=1
                            )
                            db.add(answer_obj)
                        db.commit()

                        if is_correct and wof_winner:
                            # Do not broadcast a "finished"/fully revealed phrase! Only send the winner.
                            await admin_manager.broadcast({
                                "type": "wof_winner",
                                "winner": wof_winner
                            })
                            await participant_manager.broadcast({
                                "type": "wof_winner",
                                "winner": wof_winner
                            })

                        # Continue to normal answer processing for live results display
                        # (don't skip with continue)
                    # ---- END OF WOF LOGIC ----

                    # CUSTOM: For word_cloud, always accept and ignore is_correct/scoring at this stage
                    if current_question and data["question_id"] == current_question.id and not is_word_cloud:
                        if current_question.type == "fill_in_the_blank":
                            # Use numerical scoring for fill_in_the_blank
                            score = compute_numeric_score(
                                current_question.correct_answer or "",
                                data["answer"] or ""
                            )
                            is_correct = score > 0
                            print(f"[NUMERIC DEBUG] fill_in_the_blank scoring: user='{data['answer']}', correct='{current_question.correct_answer}', score={score}, is_correct={is_correct}")
                        elif current_question.type == "pictionary":
                            # Use semantic similarity for pictionary questions
                            score, similarity = compute_semantic_score(
                                current_question.correct_answer or "",
                                data["answer"] or ""
                            )
                            is_correct = score > 0  # Any score above 0 means it passed the similarity threshold
                            print(f"[SEMANTIC DEBUG] pictionary scoring: user='{data['answer']}', correct='{current_question.correct_answer}', similarity={similarity:.3f}, score={score}, is_correct={is_correct}")
                        else:
                            # Use exact matching for other question types (like wheel_of_fortune full phrase)
                            is_correct = (data["answer"].strip().lower() == current_question.correct_answer.strip().lower())
                            if is_correct and question_start_time is not None:
                                elapsed_time = asyncio.get_event_loop().time() - question_start_time
                                seconds_remaining = max(0, 30 - elapsed_time)
                                score = int(seconds_remaining)  # Convert to integer seconds
                            else:
                                score = 0
                            print(f"[EXACT DEBUG] {current_question.type} scoring: user='{data['answer']}', correct='{current_question.correct_answer}', is_correct={is_correct}, score={score}")

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
                        print(f"[SCORING DEBUG] Word cloud answer from {participant.name}: score=0, total_score={total_score}")
                    else:
                        await participant_manager.send_personal_message({
                            "type": "personal_feedback",
                            "correct": is_correct,
                            "score": score,
                            "total_score": total_score,
                            "retry_count": existing.retry_count if existing else 1,
                            "allow_multiple": current_question.allow_multiple if current_question else True
                        }, connection_id)
                        print(f"[SCORING DEBUG] Answer from {participant.name}: correct={is_correct}, score={score}, total_score={total_score}")

                    # Notify admin of updated answers
                    answers, _ = await get_current_answers(db)
                    # Don't update leaderboard for word cloud questions (no scoring)
                    is_word_cloud = current_question and current_question.type == "word_cloud"
                    leaderboard = [] if is_word_cloud else await get_cumulative_scores(db)
                    print(f"[SCORING DEBUG] Broadcasting to admin: {len(answers)} answers, leaderboard has {len(leaderboard)} entries")
                    await admin_manager.broadcast({
                        "type": "answer_received",
                        "question_type": getattr(current_question, 'type', None),
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

def calculate_question_hash(question_data):
    """Calculate hash for deduplication"""
    hash_content = f"{question_data['type']}|{question_data['content']}|{question_data['correct_answer']}"
    if question_data.get("answers"):
        hash_content += f"|{'|'.join(sorted(question_data['answers']))}"
    return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()

@app.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket):
    # Declare all global variables at function start to avoid "used before global declaration" errors
    global current_game, current_question, current_question_index, total_questions
    global question_timer, question_start_time, word_cloud_scored
    global wof_revealed_indices, wof_reveal_task, wof_winner, wof_tile_duration

    # Establish connection and obtain a unique connection ID
    connection_id = await admin_manager.connect(websocket, "admin")

    # If a quiz is already active, send the current timer state to the new admin
    if current_game and current_game.status == "active" and current_question:
        timer_value = "Ready..." if current_question.type == "wheel_of_fortune" else 30
        await admin_manager.send_personal_message(
            {"type": "timer_update", "time_left": timer_value},
            connection_id,
        )

    # Send current database information to the admin
    current_db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///./", "")
    db = SessionLocal()
    try:
        question_count = db.query(Question).count()
        await admin_manager.send_personal_message({
            "type": "current_database_info",
            "database": current_db_path,
            "question_count": question_count
        }, connection_id)
    finally:
        db.close()

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
                                "correct_answer": current_question.correct_answer,  # Send for all question types for load testing
                            },
                            "progress": {"current": current_question_index, "total": total_questions},
                        }
                        await admin_manager.broadcast(
                            {"type": "question_pushed", "question": question_payload["question"], "progress": question_payload["progress"]}
                        )
                        await participant_manager.broadcast(question_payload)

                        # Start default 30s timer only for non-WOF questions
                        # WOF questions only start their timer when admin clicks "Start Countdown"
                        if current_question.type != "wheel_of_fortune":
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
                        await admin_manager.send_personal_message({"type": "questions_reordered"}, connection_id)
                    else:
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
                    # Handle settings sent from admin UI (including database switching)
                    s = data["settings"]

                    # Handle database switching
                    if "database_file" in s and s["database_file"]:
                        new_db = s["database_file"]
                        try:
                            # End current quiz gracefully if active
                            if current_game and current_game.status == "active":
                                await end_quiz(db)
                                await admin_manager.broadcast({"type": "quiz_ended", "reason": "database_switch"})
                                await participant_manager.broadcast({"type": "quiz_ended", "reason": "database_switch"})

                            # Switch database
                            old_db = switch_database(new_db)

                            # Reset global state (globals already declared at function start)

                            current_game = None
                            current_question = None
                            current_question_index = 0
                            total_questions = 0
                            question_timer = None
                            question_start_time = None
                            word_cloud_scored = False
                            wof_revealed_indices = None
                            wof_reveal_task = None
                            wof_winner = None

                            # Reload total questions count
                            db = SessionLocal()
                            total_questions = db.query(Question).count()
                            db.close()

                            print(f"Database switched from {old_db} to {new_db}")
                            await admin_manager.send_personal_message({
                                "type": "database_switched",
                                "new_database": new_db,
                                "total_questions": total_questions
                            }, connection_id)

                        except Exception as e:
                            print(f"Database switch failed: {e}")
                            await admin_manager.send_personal_message({
                                "type": "settings_error",
                                "error": f"Failed to switch database: {str(e)}"
                            }, connection_id)
                            continue

                    # Handle other settings and persist to YAML
                    settings_changed = False
                    if "wof_tile_duration" in s:
                        try:
                            new_duration = float(s["wof_tile_duration"])
                            if new_duration != wof_tile_duration:
                                wof_tile_duration = new_duration
                                SETTINGS['wof_tile_duration'] = new_duration
                                settings_changed = True
                        except Exception:
                            pass  # Keep previous value on invalid input

                    # Save settings to YAML if anything changed
                    if settings_changed:
                        save_settings(SETTINGS)
                        print(f"Settings updated and saved: wof_tile_duration={wof_tile_duration}")

                    await admin_manager.send_personal_message({"type": "settings_saved"}, connection_id)
                # ---------- Drawing ----------
                # Drawing updates only sent to admin (participants see via screen share)
                elif data["type"] == "drawing_stroke":
                    pass  # No longer broadcast to participants

                # ---------- Start WoF Countdown ----------
                elif data["type"] == "start_wof_countdown":
                    if current_question and current_question.type == "wheel_of_fortune":
                        phrase = current_question.correct_answer or ""
                        unique_letters = len(set(c.upper() for c in phrase if c.isalpha()))
                        timer_duration = int(unique_letters * wof_tile_duration)
                        print(f"[WoF] Starting countdown with duration: {timer_duration}s ({unique_letters} unique letters × {wof_tile_duration}s)")

                        # Send initial display update to show word-formatted board immediately
                        await broadcast_wof_state(current_question.correct_answer or "")

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
                    elif current_question.type == "fill_in_the_blank":
                        # Special handling for fill_in_the_blank: compute top 10 proportional scores
                        compute_top10_proportional_scores(
                            db,
                            current_question.id,
                            current_game.id if current_game else None,
                            current_question.correct_answer
                        )
                        # Then reveal as normal
                        reveal_payload = {
                            "type": "answer_revealed",
                            "correct_answer": current_question.correct_answer or "",
                            "question_id": current_question.id,
                            "question_type": current_question.type
                        }
                        await admin_manager.broadcast(reveal_payload)
                        await participant_manager.broadcast(reveal_payload)
                        await admin_manager.send_personal_message({"type": "reveal_confirmed"}, connection_id)
                    else:
                        # DEFAULT: legacy reveal behavior for other question types
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
        # Notify admin to reset the timer value based on question type
        timer_value = "Ready..." if current_question and current_question.type == "wheel_of_fortune" else 30
        await admin_manager.broadcast({
            "type": "timer_update",
            "time_left": timer_value
        })

    # Cancel any existing WoF letter-reveal
    if wof_reveal_task:
        wof_reveal_task.cancel()
        wof_reveal_task = None

    wof_revealed_indices = None
    wof_winner = None

    # Get next question IN PERSISTED ORDER
    question = db.query(Question).order_by(getattr(Question, "order", Question.id)).offset(current_question_index).first()
    if question:
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
    revealing letters randomly and notifying clients of current state.
    """
    global wof_revealed_indices, wof_winner
    import random

    try:
        if wof_revealed_indices is None:
            return
        while not all(wof_revealed_indices):
            # Find all indices that are still hidden (not revealed and are letters)
            hidden_indices = []
            for idx, revealed in enumerate(wof_revealed_indices):
                if not revealed and phrase[idx].isalpha():
                    hidden_indices.append(idx)

            if not hidden_indices:
                # No more letters to reveal
                await broadcast_wof_state(phrase, finished=True)
                break

            # Randomly select one hidden index
            selected_idx = random.choice(hidden_indices)
            selected_letter = phrase[selected_idx].upper()

            # Reveal ALL instances of this letter in the phrase
            for idx, char in enumerate(phrase):
                if char.upper() == selected_letter:
                    wof_revealed_indices[idx] = True

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
    Broadcasts masked phrase words with borders, revealed indices, and winner to admin only.
    Participants see the board via screen share.
    """
    words = []
    if wof_revealed_indices is not None:
        # Split phrase into words by spaces
        phrase_words = phrase.split()
        idx = 0
        for word in phrase_words:
            word_display = ""
            for char in word:
                if wof_revealed_indices[idx]:
                    word_display += char
                elif char.isalpha():
                    word_display += "_"
                else:
                    word_display += char
                idx += 1
            # Skip the space character after each word (except last)
            if idx < len(phrase) and phrase[idx] == ' ':
                idx += 1
            words.append(word_display)

    # Only send to admin - participants see via screen share
    await admin_manager.broadcast({
        "type": "wof_update",
        "words": words,
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
        # Use 60 seconds for pictionary, 30 seconds for other questions
        time_left = 60 if current_question and current_question.type == "pictionary" else 30
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
    if not current_game or current_game.id is None:
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

    # Early return if no active question/game
    if not current_question or not current_game:
        return

    question_id = getattr(current_question, "id", None)
    game_id = getattr(current_game, "id", None)
    if not question_id or not game_id:
        return

    # Fetch all answers
    answer_objs = db.query(Answer).filter(
        Answer.question_id == question_id,
        Answer.game_id == game_id
    ).all()

    answers = [(ans.user_id, ans.content.strip()) for ans in answer_objs if ans.content and ans.content.strip()]

    cluster_map, answer_to_cluster = cluster_word_cloud_answers(answers)
    total_participants = len(answers)
    for ans in answer_objs:
        # No scoring for word clouds - they are warmup questions
        ans.score = 0
        ans.is_correct = False
    db.commit()
    # Prepare for admin word cloud - show individual user counts per word
    # Count occurrences of each word (not cluster sizes)
    word_counts = {}
    for ans in answer_objs:
        word = ans.content.strip().lower()
        if word:
            word_counts[word] = word_counts.get(word, 0) + 1

    word_cloud = [
        {
            "text": word,
            "size": count,  # Individual user count, not cluster size
            "answers": [word]  # Just the word itself
        }
        for word, count in word_counts.items()
    ]
    # Sort by count descending for display
    word_cloud.sort(key=lambda x: x["size"], reverse=True)
    for ans in answer_objs:
        cluster_id = answer_to_cluster.get(ans.user_id)
        cluster_size = len(cluster_map[cluster_id]["users"]) if cluster_id is not None else 1
        await participant_manager.send_personal_message(
            {
                "type": "personal_feedback",
                "correct": False,
                "score": ans.score,
                "total_score": sum(a.score for a in db.query(Answer).filter(Answer.user_id == ans.user_id, Answer.game_id == game_id).all()),
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
        "question_id": question_id,
        "word_cloud": word_cloud,
    }
    await admin_manager.broadcast(reveal_payload)
    if admin_connection_id:
        await admin_manager.send_personal_message({"type": "reveal_confirmed"}, admin_connection_id)
    await participant_manager.broadcast(
        {"type": "word_cloud_scoring_complete", "question_id": question_id}
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
    parser = argparse.ArgumentParser(description="All-Hands Quiz Game Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server to")
    parser.add_argument("--root-path", default="", help="Root path for reverse proxy (e.g., /all-hands)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # Set root path for FastAPI if specified
    if args.root_path:
        app.root_path = args.root_path

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        root_path=args.root_path
    )
