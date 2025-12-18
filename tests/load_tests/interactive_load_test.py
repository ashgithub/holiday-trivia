#!/usr/bin/env python3
"""
Interactive Load Test Client - Connect 150 simulated users and test all question types interactively
"""

import asyncio
import json
import websockets
import time
import random
import threading
from collections import defaultdict
import sys
import ssl

class SimulatedParticipant:
    """Simulates a single quiz participant"""


    def __init__(self, user_id: int, server_url: str = "ws://localhost:8000/ws/participant"):
        self.user_id = user_id
        self.user_name = f"TestUser_{user_id:03d}"
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.current_question = None
        self.game_active = False
        self.total_score = 0

        # Disable SSL certificate verification for testing
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def connect_and_listen(self):
        """Connect to server and handle messages"""
        try:
            print(f"{self.user_name} connecting to {self.server_url}")
            async with websockets.connect(self.server_url, ssl=self.ssl_context) as websocket:
                self.websocket = websocket
                self.connected = True

                # Send join message
                join_message = {
                    "type": "join",
                    "name": self.user_name
                }
                await websocket.send(json.dumps(join_message))
                print(f"✓ {self.user_name} joined")

                # Listen for messages
                async for message in websocket:
                    await self.handle_message(message)

        except Exception as e:
            print(f"✗ {self.user_name} connection error: {e}")
            self.connected = False

    async def handle_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)

            if data["type"] == "quiz_started":
                self.game_active = True
                print(f"🎯 {self.user_name} ready for quiz")

            elif data["type"] == "question":
                self.current_question = data["question"]
                question_type = self.current_question.get("type", "fill_in_the_blank")
                print(f"❓ {self.user_name} received {question_type} question: {self.current_question['content'][:50]}...")

                # Simulate realistic thinking time (0.5-8 seconds with varied distribution)
                # Most people answer quickly (1-3s), some take longer (4-8s), few very slow
                thinking_time = random.choices(
                    [random.uniform(0.5, 2), random.uniform(2, 4), random.uniform(4, 8)],
                    weights=[0.6, 0.3, 0.1]  # 60% fast, 30% medium, 10% slow
                )[0]
                await asyncio.sleep(thinking_time)

                # Submit answer
                await self.submit_answer()

            elif data["type"] == "personal_feedback":
                score = data.get("score", 0)
                self.total_score += score
                print(f"📊 {self.user_name} scored {score} points (total: {self.total_score})")

            elif data["type"] == "quiz_ended":
                self.game_active = False
                print(f"🏁 {self.user_name} quiz ended (final score: {self.total_score})")

        except Exception as e:
            print(f"Error handling message for {self.user_name}: {e}")

    async def submit_answer(self):
        """Submit an answer based on question type"""
        if not self.current_question or not self.websocket:
            return

        question_type = self.current_question.get("type", "fill_in_the_blank")

        # Generate realistic answers for each question type
        answer = self._generate_answer_for_type(question_type)

        answer_message = {
            "type": "answer",
            "question_id": self.current_question["id"],
            "answer": answer
        }

        try:
            await self.websocket.send(json.dumps(answer_message))
            print(f"📝 {self.user_name} answered: '{answer}'")
        except Exception as e:
            print(f"Error sending answer for {self.user_name}: {e}")

    def _generate_answer_for_type(self, question_type: str) -> str:
        """Generate appropriate answers for each question type using real correct answers"""

        # Use user_id as seed for consistent but varied answers
        random.seed(self.user_id)

        correct_answer = self.current_question.get("correct_answer", "")

        # Randomly make 50-75% of answers correct for realistic testing
        correct_percentage = random.uniform(0.5, 0.75)
        is_correct = random.random() < correct_percentage

        if question_type == "word_cloud":
            # Word cloud is subjective - always generate diverse responses
            if is_correct and correct_answer and correct_answer != "auto-scored":
                answer = correct_answer
            else:
                answer = self._generate_word_cloud_answer()
        elif question_type == "multiple_choice":
            options = self.current_question.get("options", [])
            if is_correct and correct_answer:
                answer = correct_answer
            else:
                # Choose wrong option from actual available options
                wrong_options = [opt for opt in options if opt != correct_answer]
                if wrong_options:
                    answer = random.choice(wrong_options)
                else:
                    # Fallback if no wrong options available
                    answer = f"Wrong option {random.randint(1, 3)}"
        elif question_type == "fill_in_the_blank":
            if is_correct and correct_answer:
                answer = correct_answer
            else:
                # Generate wrong answers that are NOT close to the correct numerical answer
                try:
                    correct_num = float(correct_answer)
                    # Generate numbers in ranges that avoid being close to correct answer
                    # Close is defined as within 20% or 10 units, whichever is larger
                    margin = max(10, abs(correct_num) * 0.2)

                    # Generate wrong numbers in 3 ranges: below, above, and far above
                    ranges = [
                        (1, max(1, correct_num - margin - 50)),  # Well below
                        (correct_num + margin + 1, correct_num + margin + 100),  # Well above
                        (correct_num + margin + 200, correct_num + margin + 500)  # Far above
                    ]

                    # Filter out invalid ranges
                    valid_ranges = [(start, end) for start, end in ranges if start <= end]

                    if valid_ranges:
                        # Choose a range and generate a number in it
                        chosen_range = random.choice(valid_ranges)
                        wrong_num = random.randint(int(chosen_range[0]), int(chosen_range[1]))
                        answer = str(wrong_num)
                    else:
                        # Fallback if no valid ranges
                        answer = str(random.randint(100, 1000))
                except (ValueError, TypeError):
                    # If correct_answer is not numeric, generate generic wrong answers
                    wrong_answers = ["wrong", "incorrect", "no idea", "idk", "pass", "skip"]
                    answer = random.choice(wrong_answers)
        elif question_type == "pictionary":
            # Use real correct answer: "cloud" for the drawing
            if is_correct and correct_answer:
                answer = correct_answer  # "cloud"
            else:
                # Generate plausible wrong answers for cloud-themed drawing
                wrong_answers = [
                    "sky", "plane", "travel", "flight", "airplane", "mountain",
                    "ocean", "water", "sun", "moon", "star", "bird", "wing"
                ]
                answer = random.choice(wrong_answers)
        elif question_type == "wheel_of_fortune":
            # Use real correct answer: "Holiday Cloud Journey"
            if is_correct and correct_answer:
                answer = correct_answer  # "Holiday Cloud Journey"
            else:
                # Generate plausible wrong phrase guesses for travel/teamwork theme
                wrong_answers = [
                    "Holiday Team Journey", "Cloud Travel Adventure", "Holiday Travel Team",
                    "Cloud Team Holiday", "Journey Cloud Holiday", "Team Holiday Cloud",
                    "Travel Holiday Cloud", "Holiday Cloud Travel", "Cloud Holiday Team"
                ]
                answer = random.choice(wrong_answers)
        else:
            # Fallback for unknown question types
            answer = f"Sample answer {random.randint(1, 10)}"

        random.seed()  # Reset seed
        return answer

    def _generate_word_cloud_answer(self) -> str:
        """Generate diverse, realistic word cloud answers"""
        # Mix of single words and short phrases for good clustering
        word_cloud_answers = [
            # Popular responses (will create large clusters)
            "cookies", "chocolate", "family", "love", "peace", "joy",
            "cookies", "chocolate", "family", "love", "peace", "joy",  # Repeated for clustering

            # Medium frequency
            "tradition", "giving", "happiness", "warmth", "light", "hope",
            "tradition", "giving", "happiness", "warmth", "light", "hope",

            # Individual responses (smaller clusters)
            "eggnog", "fireplace", "snowflakes", "caroling", "presents",
            "hot chocolate", "fruitcake", "pine tree", "reindeer", "sleigh",
            "gingerbread", "candy cane", "stocking", "ornaments", "wreath",
            "mistletoe", "chestnuts", "roasting", "chestnuts", "roasting",  # Phrases
            "silent night", "holy night", "jingle bells", "santa claus"
        ]

        return random.choice(word_cloud_answers)

class InteractiveLoadTester:
    """Manages 150 simulated participants"""

    def __init__(self, num_users: int = 150):
        self.num_users = num_users
        self.participants = []
        self.tasks = []
        self.connected_count = 0
        self.status_thread = None
        self.running = False

        # Create participants
        for i in range(num_users):
            participant = SimulatedParticipant(i + 1)
            self.participants.append(participant)

    def start(self):
        """Start the load test with realistic staggered connections"""
        print(f"🚀 Starting Interactive Load Test with {self.num_users} users")
        print("Supports all question types: word_cloud, multiple_choice, fill_in_the_blank, pictionary, wheel_of_fortune")
        print("Connect to http://localhost:8000/admin to control the quiz")
        print("Users will join with realistic timing and respond to questions")
        print()

        self.running = True

        # Start status monitoring thread
        self.status_thread = threading.Thread(target=self._monitor_status)
        self.status_thread.daemon = True
        self.status_thread.start()

        # Start participants with staggered connections
        async def run_all():
            async def connect_with_delay(participant, delay):
                """Connect a participant after waiting for their individual delay"""
                if delay > 0:
                    await asyncio.sleep(delay)
                await participant.connect_and_listen()

            # Calculate delays for all users (spread over 10 seconds)
            tasks = []
            for i, participant in enumerate(self.participants):
                base_delay = (i / (self.num_users - 1)) * 10 if self.num_users > 1 else 0
                delay = base_delay + random.uniform(-0.5, 0.5)  # Add some randomness
                delay = max(0, delay)  # Ensure non-negative

                # Create task that will wait its delay then connect
                task = asyncio.create_task(connect_with_delay(participant, delay))
                tasks.append(task)

            # Start all tasks simultaneously - each waits their own delay
            await asyncio.gather(*tasks, return_exceptions=True)

        # Run in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(run_all())
        except KeyboardInterrupt:
            print("\n🛑 Stopping load test...")
        finally:
            loop.close()

    def stop(self):
        """Stop the load test"""
        self.running = False
        if self.status_thread:
            self.status_thread.join(timeout=1.0)
        print("✅ Load test stopped")

    def _monitor_status(self):
        """Monitor and display connection status"""
        while self.running:
            connected = sum(1 for p in self.participants if p.connected)
            if connected != self.connected_count:
                self.connected_count = connected
                print(f"📊 Connected: {connected}/{self.num_users} users")

            # Show sample of active users
            if connected >= 10:
                active_users = [p.user_name for p in self.participants if p.connected][:5]
                print(f"👥 Active users: {', '.join(active_users)}...")
                break  # Only show once when we reach 10+ users

            time.sleep(2)

def main():
    """Main entry point"""
    print("🎯 Interactive Quiz Load Tester - All Question Types")
    print("=" * 60)
    print("This tool connects 150 simulated users to test your quiz system.")
    print()
    print("Supported Question Types:")
    print("  • Word Cloud: Semantic clustering with diverse responses")
    print("  • Multiple Choice: Random selection from options")
    print("  • Fill in the Blank: Realistic text/numeric answers")
    print("  • Pictionary: Descriptive answers for drawings")
    print("  • Wheel of Fortune: Full phrase guesses")
    print()
    print("Usage:")
    print("1. Start your quiz server: python backend/main.py --host 0.0.0.0 --port 8000")
    print("2. Open admin interface: http://localhost:8000/admin")
    print("3. Run this script: python tests/load_tests/interactive_load_test.py")
    print("4. Create questions of different types in admin interface")
    print("5. Start quiz and push questions - watch 150 users respond!")
    print()
    print("Press Ctrl+C to stop the test")
    print("=" * 60)

    tester = InteractiveLoadTester(150)

    try:
        tester.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        tester.stop()

if __name__ == "__main__":
    main()
