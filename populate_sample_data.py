#!/usr/bin/env python3
"""
Sample Data Population Script for All-Hands Quiz Game

This script populates the quiz_game.db database with sample questions
covering all question types and categories for testing purposes.

Usage:
    uv run python populate_sample_data.py
"""

import sys
import os
from pathlib import Path
import json

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Import models from backend package
from models import SessionLocal, Question, Base, engine


def create_sample_questions():
    """Create sample questions for all question types and categories"""

    questions_data = [
        # Fill in the Blank Questions
        {
            "type": "fill_blank",
            "content": "The capital city of France is _______.",
            "correct_answer": "Paris",
            "category": "geography",
            "allow_multiple": True
        },
        {
            "type": "fill_blank",
            "content": "The chemical symbol for gold is _______.",
            "correct_answer": "Au",
            "category": "science",
            "allow_multiple": True
        },
        {
            "type": "fill_blank",
            "content": "World War II ended in the year _______.",
            "correct_answer": "1945",
            "category": "history",
            "allow_multiple": True
        },
        {
            "type": "fill_blank",
            "content": "The largest planet in our solar system is _______.",
            "correct_answer": "Jupiter",
            "category": "science",
            "allow_multiple": True
        },
        {
            "type": "fill_blank",
            "content": "The first computer programmer was _______.",
            "correct_answer": "Ada Lovelace",
            "category": "history",
            "allow_multiple": True
        },

        # Multiple Choice Questions
        {
            "type": "multiple_choice",
            "content": "Which of these is NOT a primary color?",
            "answers": json.dumps(["Red", "Blue", "Green", "Yellow"]),
            "correct_answer": "Green",
            "category": "science",
            "allow_multiple": False
        },
        {
            "type": "multiple_choice",
            "content": "Which continent is the largest by land area?",
            "answers": json.dumps(["Africa", "Asia", "North America", "Europe"]),
            "correct_answer": "Asia",
            "category": "geography",
            "allow_multiple": False
        },
        {
            "type": "multiple_choice",
            "content": "Who was the first President of the United States?",
            "answers": json.dumps(["Thomas Jefferson", "John Adams", "George Washington", "Benjamin Franklin"]),
            "correct_answer": "George Washington",
            "category": "history",
            "allow_multiple": False
        },
        {
            "type": "multiple_choice",
            "content": "What is the most spoken language in the world by number of native speakers?",
            "answers": json.dumps(["English", "Spanish", "Mandarin Chinese", "Hindi"]),
            "correct_answer": "Mandarin Chinese",
            "category": "general",
            "allow_multiple": False
        },
        {
            "type": "multiple_choice",
            "content": "Which of these animals is a marsupial?",
            "answers": json.dumps(["Kangaroo", "Elephant", "Lion", "Giraffe"]),
            "correct_answer": "Kangaroo",
            "category": "science",
            "allow_multiple": False
        },

        # Word Cloud Questions
        {
            "type": "word_cloud",
            "content": "Name a fruit that is typically red:",
            "correct_answer": "apple",
            "category": "general",
            "allow_multiple": True
        },
        {
            "type": "word_cloud",
            "content": "What is your favorite Christmas tradition?",
            "correct_answer": "tree",
            "category": "general",
            "allow_multiple": True
        },
        {
            "type": "word_cloud",
            "content": "Name a country in Europe:",
            "correct_answer": "France",
            "category": "geography",
            "allow_multiple": True
        },
        {
            "type": "word_cloud",
            "content": "What is something you're grateful for this year?",
            "correct_answer": "health",
            "category": "general",
            "allow_multiple": True
        },
        {
            "type": "word_cloud",
            "content": "Name a famous scientist:",
            "correct_answer": "Einstein",
            "category": "science",
            "allow_multiple": True
        },

        # Drawing Questions
        {
            "type": "drawing",
            "content": "Draw a Christmas tree with ornaments:",
            "correct_answer": "christmas tree",
            "category": "general",
            "allow_multiple": True
        },
        {
            "type": "drawing",
            "content": "Draw a simple house with a chimney:",
            "correct_answer": "house",
            "category": "general",
            "allow_multiple": True
        },
        {
            "type": "drawing",
            "content": "Draw the continents of the world:",
            "correct_answer": "world map",
            "category": "geography",
            "allow_multiple": True
        },
        {
            "type": "drawing",
            "content": "Draw a light bulb (representing innovation):",
            "correct_answer": "light bulb",
            "category": "science",
            "allow_multiple": True
        },
        {
            "type": "drawing",
            "content": "Draw a timeline showing major historical events:",
            "correct_answer": "timeline",
            "category": "history",
            "allow_multiple": True
        },

        # Wheel of Fortune Questions
        {
            "type": "wheel_of_fortune",
            "content": "Unscramble: R A P I S",
            "correct_answer": "Paris",
            "category": "geography",
            "allow_multiple": True
        },
        {
            "type": "wheel_of_fortune",
            "content": "Complete the phrase: E = mc ___",
            "correct_answer": "squared",
            "category": "science",
            "allow_multiple": True
        },
        {
            "type": "wheel_of_fortune",
            "content": "Who was the first man on the moon? (Last name)",
            "correct_answer": "Armstrong",
            "category": "history",
            "allow_multiple": True
        },
        {
            "type": "wheel_of_fortune",
            "content": "What is the color of the sky on a clear day?",
            "correct_answer": "blue",
            "category": "science",
            "allow_multiple": True
        },
        {
            "type": "wheel_of_fortune",
            "content": "What holiday is celebrated on December 25th?",
            "correct_answer": "Christmas",
            "category": "general",
            "allow_multiple": True
        }
    ]

    return questions_data


def populate_database():
    """Populate the database with sample questions"""

    print("🎄 All-Hands Quiz Game - Sample Data Population")
    print("=" * 50)

    # Create database tables
    print("📋 Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Clear existing questions
        existing_count = db.query(Question).count()
        if existing_count > 0:
            print(f"🗑️  Clearing {existing_count} existing questions...")
            db.query(Question).delete()
            db.commit()

        # Create sample questions
        questions_data = create_sample_questions()
        questions_created = 0

        print(f"📝 Creating {len(questions_data)} sample questions...")

        for question_data in questions_data:
            question = Question(**question_data)
            db.add(question)
            questions_created += 1

            # Print progress
            if questions_created % 5 == 0:
                print(f"  ✓ Created {questions_created} questions...")

        # Commit all changes
        db.commit()

        # Verify creation
        total_questions = db.query(Question).count()
        questions_by_type = {}
        questions_by_category = {}

        for question in db.query(Question).all():
            questions_by_type[question.type] = questions_by_type.get(question.type, 0) + 1
            questions_by_category[question.category] = questions_by_category.get(question.category, 0) + 1

        print("\n✅ Database populated successfully!")
        print(f"📊 Total questions: {total_questions}")
        print("\n📈 Questions by type:")
        for qtype, count in questions_by_type.items():
            print(f"   • {qtype}: {count}")

        print("\n📂 Questions by category:")
        for category, count in questions_by_category.items():
            print(f"   • {category}: {count}")

        print("\n🚀 Ready for quiz testing!")
        print("   Start the server: uv run python backend/main.py")
        print("   Open admin panel: http://localhost:8000/admin")
        print("   Use password: quizzer")
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    try:
        populate_database()
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
