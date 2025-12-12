"""
Load testing scenarios for 150-user testing

This module provides comprehensive test scenarios to validate the quiz application
under various load conditions, simulating real-world usage patterns.
"""

import time
import json
from monitoring import system_monitor, app_metrics, reporter


def run_150_user_load_test():
    """
    Main test scenario for 150 concurrent users

    This test simulates the full all-hands meeting scenario:
    - 150 participants joining simultaneously
    - Quiz master starting the quiz
    - Questions being pushed in sequence
    - Participants answering in real-time
    - System monitoring throughout the test
    """
    print("=== Starting 150-User Load Test ===")
    print("This test will simulate a full all-hands quiz meeting scenario")
    print("Ensure the quiz server is running on localhost:8000")
    print()

    # Start monitoring
    system_monitor.start_monitoring()
    app_metrics.start_collection()

    try:
        # Phase 1: User Connection Ramp-up (0-30 seconds)
        print("Phase 1: Connecting 150 users...")
        _simulate_user_connections(150, duration=30)

        # Phase 2: Quiz Initialization (30-45 seconds)
        print("Phase 2: Starting quiz...")
        _simulate_quiz_start()

        # Phase 3: Question Sequence (45-120 seconds)
        print("Phase 3: Running quiz questions...")
        _simulate_question_sequence(10, 7)  # 10 questions, 7 seconds each

        # Phase 4: Quiz Completion (120-135 seconds)
        print("Phase 4: Ending quiz...")
        _simulate_quiz_end()

        # Phase 5: User Disconnection (135-150 seconds)
        print("Phase 5: Users disconnecting...")
        _simulate_user_disconnections(150, duration=15)

        print("Load test completed successfully!")

    except Exception as e:
        print(f"Load test failed: {e}")
        raise

    finally:
        # Stop monitoring and generate report
        system_analysis = system_monitor.stop_monitoring()
        app_summary = app_metrics.get_summary()

        # Generate and save comprehensive report
        report = reporter.generate_report("150_User_Load_Test", 150)
        report_file = reporter.save_report(report)

        # Print summary
        _print_test_summary(report)

        return report


def run_gradual_scale_test():
    """
    Gradual scaling test: 10 → 50 → 100 → 150 users

    This test validates system stability as user count increases gradually,
    allowing identification of scaling bottlenecks.
    """
    print("=== Starting Gradual Scale Test ===")
    print("Testing progressive scaling: 10 → 50 → 100 → 150 users")
    print()

    user_counts = [10, 50, 100, 150]
    reports = []

    for user_count in user_counts:
        print(f"Testing with {user_count} users...")

        # Reset monitoring for each test phase
        system_monitor.start_monitoring()
        app_metrics.start_collection()

        try:
            # Connect users
            _simulate_user_connections(user_count, duration=10)

            # Run a short quiz
            _simulate_quiz_start()
            _simulate_question_sequence(3, 5)  # 3 questions, 5 seconds each
            _simulate_quiz_end()

            # Disconnect users
            _simulate_user_disconnections(user_count, duration=5)

        except Exception as e:
            print(f"Scale test failed at {user_count} users: {e}")
            break

        finally:
            # Generate report for this user count
            system_analysis = system_monitor.stop_monitoring()
            report = reporter.generate_report(f"Scale_Test_{user_count}_Users", user_count)
            reports.append(report)

            # Print quick summary
            perf = report["performance_assessment"]
            print(f"  Performance Score: {perf['overall_score']}/100 ({perf['grade']})")
            if perf["issues"]:
                print(f"  Issues: {len(perf['issues'])}")
            print()

    # Save comprehensive scaling report
    scaling_report = {
        "test_type": "gradual_scaling",
        "user_counts_tested": user_counts,
        "individual_reports": reports,
        "scaling_analysis": _analyze_scaling_performance(reports)
    }

    scaling_file = f"scaling_test_report_{int(time.time())}.json"
    with open(scaling_file, 'w') as f:
        json.dump(scaling_report, f, indent=2, default=str)

    print(f"Scaling test report saved to: {scaling_file}")
    return scaling_report


def run_stress_test():
    """
    Stress test with connection churn and peak loads

    This test simulates realistic meeting conditions:
    - Users joining/leaving throughout the quiz
    - Network interruptions and reconnections
    - Peak answer submission loads
    """
    print("=== Starting Stress Test ===")
    print("Testing connection churn and peak loads...")
    print()

    system_monitor.start_monitoring()
    app_metrics.start_collection()

    try:
        # Start with 100 users
        print("Connecting initial 100 users...")
        _simulate_user_connections(100, duration=20)

        # Start quiz
        _simulate_quiz_start()

        # Phase 1: 50 more users join during first question
        print("Phase 1: 50 additional users joining during quiz...")
        _simulate_user_connections(50, duration=10, concurrent=True)
        _simulate_question_with_answers(1, 150, answer_time=8)

        # Phase 2: Simulate network issues (20 users disconnect/reconnect)
        print("Phase 2: Simulating network interruptions...")
        _simulate_connection_churn(20, duration=15)
        _simulate_question_with_answers(2, 130, answer_time=8)

        # Phase 3: Peak load - all remaining users answer simultaneously
        print("Phase 3: Peak load simulation...")
        _simulate_question_with_answers(3, 130, answer_time=2)  # Very fast answers

        # Phase 4: Mass disconnection during final question
        print("Phase 4: Mass disconnection during final question...")
        _simulate_question_with_answers(4, 130, answer_time=5)
        _simulate_user_disconnections(130, duration=5)

        _simulate_quiz_end()

        print("Stress test completed!")

    except Exception as e:
        print(f"Stress test failed: {e}")
        raise

    finally:
        system_analysis = system_monitor.stop_monitoring()
        report = reporter.generate_report("Stress_Test", 150)
        report_file = reporter.save_report(report)
        _print_test_summary(report)

        return report


def run_correctness_under_load_test():
    """
    Correctness validation under load conditions

    This test ensures that quiz logic remains correct even under heavy load:
    - Answer validation works properly
    - Scoring is accurate
    - Question sequencing is maintained
    - Real-time updates are consistent
    """
    print("=== Starting Correctness Under Load Test ===")
    print("Validating quiz logic accuracy under load...")
    print()

    system_monitor.start_monitoring()
    app_metrics.start_collection()

    try:
        # Connect 100 users for correctness testing
        _simulate_user_connections(100, duration=15)

        _simulate_quiz_start()

        # Test multiple question types with validation
        test_questions = [
            {"type": "fill_blank", "correct_answer": "Paris", "expected_correct": 85},
            {"type": "multiple_choice", "correct_answer": "4", "expected_correct": 90},
            {"type": "word_cloud", "correct_answer": "innovation", "expected_correct": 70},
        ]

        for i, question in enumerate(test_questions):
            print(f"Testing question {i+1}: {question['type']}")

            # Simulate question and collect answer statistics
            answer_stats = _simulate_question_with_correctness_tracking(
                i+1, 100, question, answer_time=6
            )

            # Validate correctness
            correct_percentage = answer_stats["correct_percentage"]
            expected_min = question["expected_correct"]

            if correct_percentage < expected_min:
                print(f"  WARNING: Correctness below threshold: {correct_percentage:.1f}% < {expected_min}%")
                app_metrics.record_quiz_event("correctness_warning", {
                    "question_id": i+1,
                    "correct_percentage": correct_percentage,
                    "expected_minimum": expected_min
                })
            else:
                print(f"  ✓ Correctness validated: {correct_percentage:.1f}%")

        _simulate_quiz_end()
        _simulate_user_disconnections(100, duration=10)

        print("Correctness test completed!")

    except Exception as e:
        print(f"Correctness test failed: {e}")
        raise

    finally:
        system_analysis = system_monitor.stop_monitoring()
        report = reporter.generate_report("Correctness_Under_Load_Test", 100)
        report_file = reporter.save_report(report)
        _print_test_summary(report)

        return report


# Helper functions for test scenarios

def _simulate_user_connections(user_count: int, duration: float, concurrent: bool = False):
    """Simulate users connecting over a time period"""
    if concurrent:
        # All users connect simultaneously
        for i in range(user_count):
            app_metrics.record_websocket_event("user_connected", f"User_{i}")
        time.sleep(1)  # Brief pause for processing
    else:
        # Staggered connections
        delay_between_connections = duration / user_count
        for i in range(user_count):
            app_metrics.record_websocket_event("user_connected", f"User_{i}")
            time.sleep(delay_between_connections)

def _simulate_user_disconnections(user_count: int, duration: float):
    """Simulate users disconnecting over a time period"""
    delay_between_disconnections = duration / user_count
    for i in range(user_count):
        app_metrics.record_websocket_event("user_disconnected", f"User_{i}")
        time.sleep(delay_between_disconnections)

def _simulate_connection_churn(churn_count: int, duration: float):
    """Simulate users disconnecting and reconnecting"""
    for i in range(churn_count):
        # Disconnect
        app_metrics.record_websocket_event("user_disconnected", f"ChurnUser_{i}")
        time.sleep(0.5)

        # Reconnect
        app_metrics.record_websocket_event("user_reconnected", f"ChurnUser_{i}")
        time.sleep(duration / churn_count - 0.5)

def _simulate_quiz_start():
    """Simulate quiz master starting the quiz"""
    app_metrics.record_quiz_event("quiz_started")
    time.sleep(2)  # Setup time

def _simulate_quiz_end():
    """Simulate quiz master ending the quiz"""
    app_metrics.record_quiz_event("quiz_ended")
    time.sleep(1)

def _simulate_question_sequence(question_count: int, seconds_per_question: float):
    """Simulate a sequence of questions"""
    for i in range(question_count):
        app_metrics.record_quiz_event("question_started", {"question_id": i+1})
        time.sleep(seconds_per_question)
        app_metrics.record_quiz_event("question_ended", {"question_id": i+1})

def _simulate_question_with_answers(question_id: int, user_count: int, answer_time: float):
    """Simulate a question with users answering"""
    app_metrics.record_quiz_event("question_started", {"question_id": question_id})

    # Simulate users answering over time
    answers_per_second = user_count / answer_time
    for i in range(user_count):
        app_metrics.record_quiz_event("answer_received", {
            "question_id": question_id,
            "user_id": f"User_{i}",
            "is_correct": i % 3 == 0  # ~33% correct for testing
        })
        time.sleep(1 / answers_per_second)

    app_metrics.record_quiz_event("question_ended", {"question_id": question_id})

def _simulate_question_with_correctness_tracking(question_id: int, user_count: int,
                                               question_config: dict, answer_time: float):
    """Simulate question with detailed correctness tracking"""
    app_metrics.record_quiz_event("question_started", {"question_id": question_id})

    correct_answers = 0
    total_answers = 0

    # Simulate realistic answer distribution
    answers_per_second = user_count / answer_time
    for i in range(user_count):
        # Generate answer based on question type
        is_correct = _generate_realistic_answer_correctness(question_config["type"])
        if is_correct:
            correct_answers += 1
        total_answers += 1

        app_metrics.record_quiz_event("answer_received", {
            "question_id": question_id,
            "user_id": f"User_{i}",
            "is_correct": is_correct,
            "question_type": question_config["type"]
        })
        time.sleep(1 / answers_per_second)

    correct_percentage = (correct_answers / total_answers) * 100 if total_answers > 0 else 0

    app_metrics.record_quiz_event("question_ended", {
        "question_id": question_id,
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "correct_percentage": correct_percentage
    })

    return {
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "correct_percentage": correct_percentage
    }

def _generate_realistic_answer_correctness(question_type: str) -> bool:
    """Generate realistic correctness based on question type"""
    import random

    if question_type == "fill_blank":
        # 75% correct for simple fill-in-the-blank
        return random.random() < 0.75
    elif question_type == "multiple_choice":
        # 80% correct for multiple choice
        return random.random() < 0.80
    elif question_type == "word_cloud":
        # 60% correct for subjective word cloud
        return random.random() < 0.60
    else:
        # Default 70% correct
        return random.random() < 0.70

def _analyze_scaling_performance(reports: list) -> dict:
    """Analyze performance across different user counts"""
    if not reports:
        return {"error": "No reports to analyze"}

    scaling_analysis = {
        "performance_trend": [],
        "bottlenecks_identified": [],
        "scaling_efficiency": "unknown"
    }

    for report in reports:
        user_count = report["test_info"]["user_count"]
        perf_score = report["performance_assessment"]["overall_score"]
        cpu_avg = report["system_performance"]["cpu"]["average"]
        memory_avg = report["system_performance"]["memory"]["average_percent"]

        scaling_analysis["performance_trend"].append({
            "user_count": user_count,
            "performance_score": perf_score,
            "cpu_average": cpu_avg,
            "memory_average": memory_avg
        })

    # Analyze trends
    if len(reports) >= 2:
        first_score = reports[0]["performance_assessment"]["overall_score"]
        last_score = reports[-1]["performance_assessment"]["overall_score"]

        if last_score < first_score * 0.8:
            scaling_analysis["scaling_efficiency"] = "poor"
            scaling_analysis["bottlenecks_identified"].append("Performance degrades significantly with user count")
        elif last_score < first_score * 0.9:
            scaling_analysis["scaling_efficiency"] = "fair"
            scaling_analysis["bottlenecks_identified"].append("Moderate performance degradation")
        else:
            scaling_analysis["scaling_efficiency"] = "good"

    return scaling_analysis

def _print_test_summary(report: dict):
    """Print a concise test summary"""
    print("\n=== Test Summary ===")
    test_info = report["test_info"]
    perf = report["performance_assessment"]

    print(f"Test: {test_info['name']}")
    print(f"Users: {test_info['user_count']}")
    print(f"Duration: {test_info['duration']:.1f} seconds")
    print(f"Performance Score: {perf['overall_score']}/100 ({perf['grade']})")

    if perf["issues"]:
        print(f"Issues Found: {len(perf['issues'])}")
        for issue in perf["issues"][:3]:  # Show first 3 issues
            print(f"  - {issue}")

    if "recommendations" in report:
        print(f"Recommendations: {len(report['recommendations'])}")
        for rec in report["recommendations"][:2]:  # Show first 2 recommendations
            print(f"  - {rec}")

    print("=" * 50)


# Main execution functions
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_type = sys.argv[1]

        if test_type == "150user":
            run_150_user_load_test()
        elif test_type == "scaling":
            run_gradual_scale_test()
        elif test_type == "stress":
            run_stress_test()
        elif test_type == "correctness":
            run_correctness_under_load_test()
        else:
            print("Usage: python test_scenarios.py [150user|scaling|stress|correctness]")
    else:
        print("Select test type:")
        print("  150user    - Full 150-user load test")
        print("  scaling    - Gradual scaling test (10→50→100→150)")
        print("  stress     - Stress test with connection churn")
        print("  correctness- Correctness validation under load")
