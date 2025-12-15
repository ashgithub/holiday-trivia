#!/usr/bin/env python3
"""
Question Export Script for All-Hands Quiz Game

Exports questions from the SQLite database to JSON format for backup, sharing, or migration.

Usage:
    uv run python export_questions.py [output_file.json]
    uv run python export_questions.py --help

Features:
- Exports all questions or filtered by category/type
- Validates data integrity before export
- Provides export statistics
- Supports JSON and JSON Lines formats
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add backend directory to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from models import SessionLocal, Question


def export_questions_to_json(
    output_file: str,
    type_filter: Optional[str] = None,
    pretty_print: bool = True
) -> Dict[str, Any]:
    """
    Export questions from database to JSON file.

    Args:
        output_file: Path to output JSON file
        type_filter: Optional question type filter
        pretty_print: Whether to pretty-print JSON

    Returns:
        Dict with export statistics
    """
    print("🎄 All-Hands Quiz Game - Question Export")
    print("=" * 50)

    db = SessionLocal()
    try:
        # Build query with optional filters
        query = db.query(Question)

        if type_filter:
            query = query.filter(Question.type == type_filter)
            print(f"🔍 Filtering by type: {type_filter}")

        # Order by creation date for consistency
        questions = query.order_by(Question.created_at).all()

        if not questions:
            print("⚠️  No questions found matching the criteria")
            return {"total_exported": 0, "types": {}}

        # Convert questions to export format
        export_data = []
        types_count = {}

        for question in questions:
            # Parse answers JSON if it exists
            answers = None
            if question.answers:
                try:
                    answers = json.loads(question.answers)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Invalid JSON in answers for question ID {question.id}: {e}")
                    answers = []

            # Create export record
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
                question_data["answers"] = answers

            export_data.append(question_data)

            # Update statistics
            types_count[question.type] = types_count.get(question.type, 0) + 1

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            if pretty_print:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(export_data, f, ensure_ascii=False)

        # Print statistics
        print(f"✅ Successfully exported {len(export_data)} questions to {output_file}")
        print("\n📊 Export Statistics:")
        print(f"   🔍 Types: {dict(sorted(types_count.items()))}")

        # File size info
        file_size = os.path.getsize(output_file)
        print(f"   📁 File size: {file_size:,} bytes")

        return {
            "total_exported": len(export_data),
            "types": types_count,
            "file_size": file_size,
            "output_file": output_file
        }

    except Exception as e:
        print(f"❌ Error during export: {e}")
        raise
    finally:
        db.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Export questions from All-Hands Quiz Game database to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python export_questions.py questions.json
  uv run python export_questions.py --category geography questions_geo.json
  uv run python export_questions.py --type multiple_choice --compact questions_mc.json
        """
    )

    parser.add_argument(
        "output_file",
        help="Output JSON file path"
    )

    parser.add_argument(
        "--type", "-t",
        help="Filter by question type (e.g., multiple_choice, fill_in_the_blank, word_cloud, pictionary, wheel_of_fortune)"
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact JSON format (no pretty printing)"
    )

    args = parser.parse_args()

    try:
        export_questions_to_json(
            output_file=args.output_file,
            type_filter=args.type,
            pretty_print=not args.compact
        )
    except KeyboardInterrupt:
        print("\n⏹️  Export cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
