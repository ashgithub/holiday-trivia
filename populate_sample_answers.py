#!/usr/bin/env python3
"""
Sample Answers Population Script for All-Hands Quiz Game

This script populates the database with sample users and answers
to test the scoring system, ensuring correct answers exist for all questions.

Usage:
    python populate_sample_answers.py
"""

import sys
import os
from pathlib import Path
import json
import random
from datetime import datetime, timedelta
import uuid

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Import models from backend package
from models import SessionLocal, User, Question, Game, Answer, Base, engine


def create_sample_users(count=50):
    """Create sample users with realistic names"""

    first_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Ivy", "Jack", "Kate", "Liam", "Maya", "Noah", "Olivia", "Peter",
        "Quinn", "Ryan", "Sophia", "Thomas", "Uma", "Victor", "Wendy", "Xavier",
        "Yara", "Zach", "Anna", "Brian", "Clara", "David", "Emma", "Felix",
        "Gina", "Harry", "Iris", "James", "Kara", "Leo", "Mia", "Nathan",
        "Owen", "Paula", "Quincy", "Rachel", "Sam", "Tina", "Uri", "Vera"
    ]

    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
        "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
        "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
        "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell"
    ]

    users = []
    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"

        user = User(
            name=full_name,
            role="participant",
            session_id=str(uuid.uuid4())
        )
        users.append(user)

    return users


def get_fill_blank_answers(correct_answer):
    """Generate realistic answers for fill-in-the-blank questions"""
    answers = []

    # Always include the correct answer multiple times
    answers.extend([correct_answer] * random.randint(5, 10))

    # Add close but incorrect answers
    if correct_answer.replace(" ", "").isdigit():
        # Numeric answers - add nearby numbers
        base_num = int(correct_answer)
        for i in range(10):
            offset = random.randint(1, 50)
            wrong_num = base_num + random.choice([-1, 1]) * offset
            answers.append(str(wrong_num))
    else:
        # Text answers - add common misspellings/variations
        variations = {
            "Paris": ["paris", "Pari", "Pariss", "Pairs", "Parie"],
            "Au": ["Gold", "AU", "au", "A", "Ag"],
            "1945": ["1944", "1946", "1947", "1939", "1950"],
            "Jupiter": ["Saturn", "Mars", "Venus", "jupiter", "Jupitar"],
            "Ada Lovelace": ["Ada", "Lovelace", "ada lovelace", "Ada Love", "Charles Babbage"]
        }
        if correct_answer in variations:
            answers.extend(variations[correct_answer])

    # Add random incorrect answers to reach total
    random_answers = [
        "wrong", "incorrect", "idk", "no idea", "?", "skip",
        "don't know", "pass", "random", "test", "answer"
    ]

    while len(answers) < 30:
        answers.append(random.choice(random_answers))

    return answers


def get_multiple_choice_answers(correct_answer, options):
    """Generate answers for multiple choice questions"""
    answers = []

    # Parse options if they're JSON string
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except:
            options = [correct_answer, "Wrong1", "Wrong2", "Wrong3"]

    # Many users choose correct answer
    answers.extend([correct_answer] * random.randint(15, 25))

    # Others choose wrong answers
    wrong_options = [opt for opt in options if opt != correct_answer]
    for wrong_opt in wrong_options:
        answers.extend([wrong_opt] * random.randint(5, 10))

    return answers


def get_word_cloud_answers(correct_answer):
    """Generate diverse answers for word cloud questions"""
    base_answers = [
        "apple", "banana", "orange", "grape", "strawberry", "blueberry",
        "christmas", "tree", "lights", "presents", "family", "food",
        "france", "germany", "italy", "spain", "england", "poland",
        "health", "family", "friends", "home", "job", "food",
        "einstein", "newton", "tesla", "darwin", "curie", "hawking"
    ]

    answers = []
    # Mix of correct and varied answers
    answers.extend([correct_answer] * random.randint(5, 10))

    for _ in range(25):
        answers.append(random.choice(base_answers))

    return answers


def populate_sample_answers():
    """Populate database with sample users and answers"""

    print("🎄 All-Hands Quiz Game - Sample Answers Population")
    print("=" * 55)

    db = SessionLocal()

    try:
        # Create sample users
        print("👥 Creating 50 sample users...")
        users = create_sample_users(50)
        for user in users:
            db.add(user)
        db.commit()

        # Create a sample game
        print("🎮 Creating sample game...")
        game = Game(status="active")
        db.add(game)
        db.commit()
        db.refresh(game)

        # Get all questions
        questions = db.query(Question).order_by(Question.order).all()
        print(f"📝 Found {len(questions)} questions to answer")

        total_answers = 0

        # For each question, generate answers from users
        for question in questions:
            print(f"  Answering: {question.content[:50]}...")

            # Randomly select which users will answer this question (70-90% participation)
            num_answering = random.randint(int(0.7 * len(users)), int(0.9 * len(users)))
            answering_users = random.sample(users, num_answering)

            answers_content = []

            # Generate appropriate answers based on question type
            if question.type == "fill_in_the_blank":
                answers_content = get_fill_blank_answers(question.correct_answer)
            elif question.type == "multiple_choice":
                answers_content = get_multiple_choice_answers(question.correct_answer, question.answers)
            elif question.type == "word_cloud":
                answers_content = get_word_cloud_answers(question.correct_answer)
            elif question.type == "wheel_of_fortune":
                # Mix of correct and incorrect attempts
                answers_content = [question.correct_answer] * random.randint(3, 8)
                wrong_attempts = ["wrong", "incorrect", "no", "idk", "pass", "skip"]
                answers_content.extend(random.choices(wrong_attempts, k=20))
            elif question.type == "pictionary":
                # Semantic variations
                answers_content = [question.correct_answer] * random.randint(5, 10)
                variations = ["similar", "close", "almost", "near", "kind of"]
                answers_content.extend(random.choices(variations, k=15))

            # Shuffle users and assign answers
            random.shuffle(answering_users)
            num_answers = min(len(answering_users), len(answers_content))

            base_time = datetime.utcnow() - timedelta(minutes=30)  # Quiz started 30 min ago

            for i, user in enumerate(answering_users[:num_answers]):
                answer_content = answers_content[i % len(answers_content)]

                # Calculate score based on question type
                score = 0
                is_correct = False

                if question.type == "fill_in_the_blank":
                    # Check if exact match
                    if answer_content.strip().lower() == question.correct_answer.strip().lower():
                        score = 30  # Exact match gets 30
                        is_correct = True
                    # For now, non-exact get 0 (will be adjusted by proportional scoring later)
                elif question.type == "multiple_choice":
                    is_correct = (answer_content == question.correct_answer)
                    if is_correct:
                        # Simulate time-based scoring (20-30 points)
                        score = random.randint(20, 30)
                elif question.type == "wheel_of_fortune":
                    is_correct = (answer_content.strip().lower() == question.correct_answer.strip().lower())
                    if is_correct:
                        score = random.randint(25, 30)  # Time-based for correct
                elif question.type == "pictionary":
                    # Simple semantic check
                    is_correct = (answer_content.strip().lower() == question.correct_answer.strip().lower())
                    if is_correct:
                        score = random.randint(20, 30)
                # word_cloud gets 0 score as before

                # Create answer with timestamp (simulate quiz progression)
                answer_time = base_time + timedelta(seconds=i * 2)  # 2 seconds between answers

                answer = Answer(
                    user_id=user.id,
                    question_id=question.id,
                    game_id=game.id,
                    content=answer_content,
                    is_correct=is_correct,
                    score=score,
                    timestamp=answer_time
                )
                db.add(answer)
                total_answers += 1

        db.commit()

        # Now run proportional scoring for fill-in-the-blank questions
        print("🔢 Running proportional scoring for fill-in-the-blank questions...")
        from main import compute_top10_proportional_scores

        fill_blank_questions = db.query(Question).filter(Question.type == "fill_in_the_blank").all()
        for question in fill_blank_questions:
            compute_top10_proportional_scores(db, question.id, game.id, question.correct_answer)

        db.commit()

        # Verification
        print("\n✅ Sample data populated successfully!")
        print(f"👥 Users created: {len(users)}")
        print(f"📊 Total answers: {total_answers}")

        # Check distribution
        answer_counts = db.query(Question.type, Question.content,
                               db.func.count(Answer.id)).join(Answer).group_by(Question.id).all()

        print("\n📈 Answers per question:")
        for qtype, content, count in answer_counts:
            preview = content[:40] + "..." if len(content) > 40 else content
            print(f"   • {qtype}: {count} answers - {preview}")

        # Check correct answers
        correct_counts = db.query(Question.type, db.func.count(Answer.id)).join(Answer).filter(
            Answer.is_correct == True).group_by(Question.type).all()

        print("\n✅ Correct answers by type:")
        for qtype, count in correct_counts:
            print(f"   • {qtype}: {count} correct answers")

        print("\n🚀 Database ready for testing!")
        print("   Start server: python backend/main.py")
        print("   Admin panel: http://localhost:8000/admin")

    except Exception as e:
        print(f"❌ Error populating sample answers: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    try:
        populate_sample_answers()
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
