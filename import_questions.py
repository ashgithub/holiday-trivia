#!/usr/bin/env python3
"""
Question Import Script for All-Hands Quiz Game

Imports questions from JSON format into the SQLite database.

Usage:
    uv run python import_questions.py [input_file.json]
    uv run python import_questions.py --help

Features:
- Validates question data before import
- Supports dry-run mode for testing
- Handles duplicates and conflicts
- Provides detailed import statistics
- Preserves question ordering
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib

# Add backend directory to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from models import SessionLocal, Question

# Allowed question types (must match backend validation)
ALLOWED_QUESTION_TYPES = {
    "fill_in_the_blank",
    "multiple_choice",
    "word_cloud",
    "pictionary",
    "wheel_of_fortune"
}

# Legacy type mappings for backward compatibility
TYPE_MAPPINGS = {
    "fill_blank": "fill_in_the_blank",
    "multiplechoice": "multiple_choice",
    "mcq": "multiple_choice",
    "drawing": "pictionary"  # drawing was renamed to pictionary
}


def validate_question_data(question_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a single question's data structure.

    Args:
        question_data: Question data dictionary

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Required fields
    required_fields = ["type", "content", "correct_answer", "category"]
    for field in required_fields:
        if field not in question_data or not question_data[field]:
            errors.append(f"Missing or empty required field: {field}")

    if errors:
        return False, errors

    # Validate question type
    question_type = question_data.get("type", "").strip()
    if question_type not in ALLOWED_QUESTION_TYPES:
        # Try legacy mapping
        if question_type in TYPE_MAPPINGS:
            question_data["type"] = TYPE_MAPPINGS[question_type]
        else:
            errors.append(f"Invalid question type '{question_type}'. Must be one of: {sorted(ALLOWED_QUESTION_TYPES)}")

    # Validate type-specific requirements
    if question_data["type"] in ["multiple_choice", "multiplechoice", "mcq"]:
        if "answers" not in question_data or not isinstance(question_data["answers"], list):
            errors.append("Multiple choice questions must have an 'answers' array")
        elif len(question_data["answers"]) < 2:
            errors.append("Multiple choice questions must have at least 2 answer options")
        elif question_data["correct_answer"] not in question_data["answers"]:
            errors.append("Correct answer must be one of the provided answer options")

    # Validate allow_multiple (default to True for backward compatibility)
    if "allow_multiple" not in question_data:
        question_data["allow_multiple"] = True
    elif not isinstance(question_data["allow_multiple"], bool):
        errors.append("allow_multiple must be a boolean value")

    # Validate category
    if not isinstance(question_data["category"], str) or not question_data["category"].strip():
        errors.append("Category must be a non-empty string")

    return len(errors) == 0, errors


def calculate_question_hash(question_data: Dict[str, Any]) -> str:
    """
    Calculate a hash for question deduplication based on content and answer.

    Args:
        question_data: Question data dictionary

    Returns:
        SHA256 hash string
    """
    # Create a normalized string for hashing
    hash_content = f"{question_data['type']}|{question_data['content']}|{question_data['correct_answer']}"
    if question_data.get("answers"):
        hash_content += f"|{'|'.join(sorted(question_data['answers']))}"

    return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()


def import_questions_from_json(
    input_file: str,
    dry_run: bool = False,
    skip_duplicates: bool = True,
    update_existing: bool = False,
    preserve_order: bool = True,
    drop_existing: bool = False
) -> Dict[str, Any]:
    """
    Import questions from JSON file to database.

    Args:
        input_file: Path to input JSON file
        dry_run: If True, only validate without importing
        skip_duplicates: Skip questions that appear to be duplicates
        update_existing: Update existing questions instead of skipping
        preserve_order: Preserve order field from import data

    Returns:
        Dict with import statistics
    """
    print("🎄 All-Hands Quiz Game - Question Import")
    print("=" * 50)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to database")

    # Read and parse JSON file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in input file: {e}")

    if not isinstance(import_data, list):
        raise ValueError("Input file must contain a JSON array of questions")

    print(f"📁 Reading {len(import_data)} questions from {input_file}")

    # Validate all questions first
    valid_questions = []
    validation_errors = []
    question_hashes = set()

    for i, question_data in enumerate(import_data, 1):
        is_valid, errors = validate_question_data(question_data)

        if not is_valid:
            validation_errors.append({
                "question_index": i,
                "data": question_data,
                "errors": errors
            })
            continue

        # Check for duplicates within import file
        question_hash = calculate_question_hash(question_data)
        if question_hash in question_hashes:
            if skip_duplicates:
                print(f"⚠️  Skipping duplicate question {i} (same content as previous)")
                continue

        question_hashes.add(question_hash)
        valid_questions.append((i, question_data))

    if validation_errors:
        print(f"❌ Found {len(validation_errors)} validation errors:")
        for error in validation_errors[:5]:  # Show first 5 errors
            print(f"   Question {error['question_index']}: {', '.join(error['errors'])}")
        if len(validation_errors) > 5:
            print(f"   ... and {len(validation_errors) - 5} more errors")

        if not dry_run:
            raise ValueError(f"Cannot import due to {len(validation_errors)} validation errors. Use --dry-run to see all issues.")

    print(f"✅ Validation passed for {len(valid_questions)} questions")

    if dry_run:
        print("\n📊 Dry Run Statistics:")
        categories = {}
        types = {}
        for _, q in valid_questions:
            categories[q["category"]] = categories.get(q["category"], 0) + 1
            types[q["type"]] = types.get(q["type"], 0) + 1

        print(f"   📂 Categories: {dict(sorted(categories.items()))}")
        print(f"   🔍 Types: {dict(sorted(types.items()))}")
        return {
            "dry_run": True,
            "valid_questions": len(valid_questions),
            "validation_errors": len(validation_errors),
            "categories": categories,
            "types": types
        }

    # Perform actual import
    db = SessionLocal()
    try:
        imported = 0
        skipped = 0
        updated = 0
        dropped = 0

        # Drop existing questions if requested
        if drop_existing:
            existing_count = db.query(Question).count()
            if existing_count > 0:
                print(f"🗑️  Dropping {existing_count} existing questions...")
                db.query(Question).delete()
                db.commit()
                dropped = existing_count
                print(f"✅ Dropped {dropped} existing questions")

        # Get existing question hashes for deduplication (only if not dropping all)
        existing_hashes = {}
        if not drop_existing and (skip_duplicates or update_existing):
            existing_questions = db.query(Question).all()
            for eq in existing_questions:
                # Recreate hash for existing question
                hash_data = {
                    "type": eq.type,
                    "content": eq.content,
                    "correct_answer": eq.correct_answer,
                    "answers": json.loads(eq.answers) if eq.answers else None
                }
                existing_hashes[calculate_question_hash(hash_data)] = eq

        # Determine next order value
        max_order = db.query(Question).count()  # Use count as next order

        for original_index, question_data in valid_questions:
            question_hash = calculate_question_hash(question_data)

            # Check for existing question
            existing_question = existing_hashes.get(question_hash)
            if existing_question:
                if skip_duplicates:
                    print(f"⏭️  Skipping duplicate question {original_index} (already exists)")
                    skipped += 1
                    continue
                elif update_existing:
                    # Update existing question
                    existing_question.type = question_data["type"]
                    existing_question.content = question_data["content"]
                    existing_question.correct_answer = question_data["correct_answer"]
                    existing_question.category = question_data["category"]
                    existing_question.allow_multiple = question_data["allow_multiple"]

                    if question_data["type"] in ["multiple_choice", "multiplechoice", "mcq"]:
                        existing_question.answers = json.dumps(question_data["answers"])
                    else:
                        existing_question.answers = None

                    if preserve_order and "order" in question_data:
                        existing_question.order = question_data["order"]

                    updated += 1
                    continue

            # Create new question
            new_question = Question(
                type=question_data["type"],
                content=question_data["content"],
                correct_answer=question_data["correct_answer"],
                category=question_data["category"],
                allow_multiple=question_data["allow_multiple"],
                answers=json.dumps(question_data["answers"]) if question_data.get("answers") else None,
                order=question_data.get("order", max_order + imported) if preserve_order else max_order + imported
            )

            db.add(new_question)
            imported += 1

            if imported % 10 == 0:
                print(f"  ✓ Imported {imported} questions...")

        db.commit()

        print(f"\n✅ Import completed successfully!")
        print(f"📊 Import Statistics:")
        print(f"   ➕ Imported: {imported}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   🔄 Updated: {updated}")

        # Final counts
        total_questions = db.query(Question).count()
        print(f"   📊 Total questions in database: {total_questions}")

        return {
            "imported": imported,
            "skipped": skipped,
            "updated": updated,
            "total_in_db": total_questions,
            "validation_errors": len(validation_errors)
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Error during import: {e}")
        raise
    finally:
        db.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Import questions from JSON file to All-Hands Quiz Game database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python import_questions.py questions.json
  uv run python import_questions.py --dry-run questions.json
  uv run python import_questions.py --update-existing --no-skip-duplicates questions.json
  uv run python import_questions.py --drop-existing questions.json  # WARNING: Deletes all existing questions!
        """
    )

    parser.add_argument(
        "input_file",
        help="Input JSON file path"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate questions without importing (no database changes)"
    )

    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        default=True,
        help="Skip questions that appear to be duplicates (default: True)"
    )

    parser.add_argument(
        "--no-skip-duplicates",
        action="store_false",
        dest="skip_duplicates",
        help="Do not skip duplicate questions"
    )

    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing questions instead of skipping duplicates"
    )

    parser.add_argument(
        "--no-preserve-order",
        action="store_true",
        help="Do not preserve question order from import data"
    )

    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing questions before importing (WARNING: This will delete all current questions)"
    )

    args = parser.parse_args()

    try:
        result = import_questions_from_json(
            input_file=args.input_file,
            dry_run=args.dry_run,
            skip_duplicates=args.skip_duplicates,
            update_existing=args.update_existing,
            preserve_order=not args.no_preserve_order,
            drop_existing=args.drop_existing
        )

        if args.dry_run:
            print(f"\n🔍 Dry run completed. Found {result['valid_questions']} valid questions.")
        else:
            print(f"\n✅ Import completed. {result['imported']} questions imported.")

    except KeyboardInterrupt:
        print("\n⏹️  Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
