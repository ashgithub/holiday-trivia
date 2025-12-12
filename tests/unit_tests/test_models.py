"""
Unit tests for database models and core business logic
"""

import pytest
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from models import User, Question, Game, Answer, SessionLocal, engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    # Create test database
    test_db_path = "/tmp/test_quiz.db"

    # Use in-memory SQLite for testing
    from sqlalchemy import create_engine
    test_engine = create_engine("sqlite:///:memory:")

    # Create all tables
    from backend.models import Base
    Base.metadata.create_all(bind=test_engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Clean up
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


class TestUserModel:
    """Test User model functionality"""

    def test_user_creation(self, db_session):
        """Test creating a new user"""
        user = User(
            name="Test User",
            role="participant",
            session_id="test_session_123"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.name == "Test User"
        assert user.role == "participant"
        assert user.session_id == "test_session_123"
        assert isinstance(user.created_at, datetime)

    def test_user_roles(self, db_session):
        """Test different user roles"""
        participant = User(name="Participant", role="participant")
        admin = User(name="Admin", role="quiz_master")

        db_session.add_all([participant, admin])
        db_session.commit()

        assert participant.role == "participant"
        assert admin.role == "quiz_master"


class TestQuestionModel:
    """Test Question model functionality"""

    def test_question_creation(self, db_session):
        """Test creating a question"""
        question = Question(
            type="fill_blank",
            content="What is the capital of France?",
            correct_answer="Paris",
            category="geography",
            allow_multiple=True
        )
        db_session.add(question)
        db_session.commit()
        db_session.refresh(question)

        assert question.id is not None
        assert question.type == "fill_blank"
        assert question.content == "What is the capital of France?"
        assert question.correct_answer == "Paris"
        assert question.category == "geography"
        assert question.allow_multiple is True

    def test_multiple_choice_question(self, db_session):
        """Test multiple choice question with options"""
        import json
        question = Question(
            type="multiple_choice",
            content="What is 2 + 2?",
            correct_answer="4",
            answers=json.dumps(["2", "3", "4", "5"]),
            allow_multiple=False
        )
        db_session.add(question)
        db_session.commit()
        db_session.refresh(question)

        assert question.type == "multiple_choice"
        assert json.loads(question.answers) == ["2", "3", "4", "5"]

    def test_question_categories(self, db_session):
        """Test question categorization"""
        categories = ["geography", "history", "science", "general"]

        for category in categories:
            question = Question(
                type="fill_blank",
                content=f"Question in {category}",
                correct_answer="Answer",
                category=category
            )
            db_session.add(question)

        db_session.commit()

        # Verify categories are stored correctly
        for category in categories:
            q = db_session.query(Question).filter(Question.category == category).first()
            assert q is not None
            assert q.category == category


class TestGameModel:
    """Test Game model functionality"""

    def test_game_creation(self, db_session):
        """Test creating a game session"""
        game = Game(status="active")
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.id is not None
        assert game.status == "active"
        assert game.created_at is not None
        assert game.finished_at is None

    def test_game_lifecycle(self, db_session):
        """Test game status transitions"""
        game = Game(status="active")
        db_session.add(game)
        db_session.commit()

        # Start game
        assert game.status == "active"

        # End game
        game.status = "finished"
        game.finished_at = datetime.utcnow()
        db_session.commit()

        assert game.status == "finished"
        assert game.finished_at is not None


class TestAnswerModel:
    """Test Answer model functionality"""

    def test_answer_creation(self, db_session):
        """Test creating an answer"""
        # Create related objects first
        user = User(name="Test User", role="participant")
        question = Question(
            type="fill_blank",
            content="Test question?",
            correct_answer="Test answer"
        )
        game = Game(status="active")

        db_session.add_all([user, question, game])
        db_session.commit()

        # Create answer
        answer = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="User answer",
            is_correct=True,
            retry_count=1
        )
        db_session.add(answer)
        db_session.commit()
        db_session.refresh(answer)

        assert answer.id is not None
        assert answer.user_id == user.id
        assert answer.question_id == question.id
        assert answer.game_id == game.id
        assert answer.content == "User answer"
        assert answer.is_correct is True
        assert answer.retry_count == 1
        assert answer.timestamp is not None

    def test_answer_correctness_validation(self, db_session):
        """Test answer correctness validation"""
        user = User(name="Test User", role="participant")
        question = Question(
            type="fill_blank",
            content="What is 2+2?",
            correct_answer="4"
        )
        game = Game(status="active")

        db_session.add_all([user, question, game])
        db_session.commit()

        # Test correct answer
        correct_answer = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="4",
            is_correct=True
        )

        # Test incorrect answer
        incorrect_answer = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="5",
            is_correct=False
        )

        db_session.add_all([correct_answer, incorrect_answer])
        db_session.commit()

        assert correct_answer.is_correct is True
        assert incorrect_answer.is_correct is False

    def test_answer_retry_count(self, db_session):
        """Test answer retry counting"""
        user = User(name="Test User", role="participant")
        question = Question(
            type="fill_blank",
            content="Test question?",
            correct_answer="Correct"
        )
        game = Game(status="active")

        db_session.add_all([user, question, game])
        db_session.commit()

        # First attempt
        answer1 = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="Wrong",
            is_correct=False,
            retry_count=1
        )

        # Second attempt
        answer2 = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="Correct",
            is_correct=True,
            retry_count=2
        )

        db_session.add_all([answer1, answer2])
        db_session.commit()

        assert answer1.retry_count == 1
        assert answer2.retry_count == 2


class TestModelRelationships:
    """Test relationships between models"""

    def test_user_answers_relationship(self, db_session):
        """Test User-Answer relationship"""
        user = User(name="Test User", role="participant")
        question = Question(
            type="fill_blank",
            content="Test?",
            correct_answer="Answer"
        )
        game = Game(status="active")

        db_session.add_all([user, question, game])
        db_session.commit()

        answer = Answer(
            user_id=user.id,
            question_id=question.id,
            game_id=game.id,
            content="Answer",
            is_correct=True
        )
        db_session.add(answer)
        db_session.commit()

        # Test relationship from user to answers
        user_answers = db_session.query(Answer).filter(Answer.user_id == user.id).all()
        assert len(user_answers) == 1
        assert user_answers[0].content == "Answer"

    def test_question_answers_relationship(self, db_session):
        """Test Question-Answer relationship"""
        question = Question(
            type="fill_blank",
            content="Test?",
            correct_answer="Answer"
        )
        user = User(name="Test User", role="participant")
        game = Game(status="active")

        db_session.add_all([question, user, game])
        db_session.commit()

        answers = []
        for i in range(3):
            answer = Answer(
                user_id=user.id,
                question_id=question.id,
                game_id=game.id,
                content=f"Answer {i}",
                is_correct=(i == 2)  # Only last answer is correct
            )
            answers.append(answer)

        db_session.add_all(answers)
        db_session.commit()

        # Test relationship from question to answers
        question_answers = db_session.query(Answer).filter(Answer.question_id == question.id).all()
        assert len(question_answers) == 3

        correct_answers = [a for a in question_answers if a.is_correct]
        assert len(correct_answers) == 1
