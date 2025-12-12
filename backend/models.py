from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./quiz_game.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    """User model for quiz master and participants"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "quiz_master" or "participant"
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    """Question model"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # "fill_blank", "word_cloud", "drawing", "wheel_fortune", "multiple_choice"
    content = Column(Text, nullable=False)
    answers = Column(Text)  # JSON string for multiple choice options
    correct_answer = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    allow_multiple = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Game(Base):
    """Game session model"""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="waiting")  # "waiting", "active", "finished"
    current_question_id = Column(Integer, ForeignKey("questions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)

    current_question = relationship("Question")

class Answer(Base):
    """Answer submission model"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    score = Column(Integer, default=0)  # Time-based score (seconds remaining if correct, 0 if wrong)
    retry_count = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    question = relationship("Question")
    game = relationship("Game")

# Create tables
Base.metadata.create_all(bind=engine)
