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


    def __init__(self, user_id: int, server_url: str = "wss://venus.aisandbox.ugbu.oraclepdemos.com/trivia/ws/participant"):
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

                # Simulate thinking time (1-5 seconds)
                await asyncio.sleep(random.uniform(1, 5))

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
        """Generate appropriate answers for each question type"""

        # Use user_id as seed for consistent but varied answers
        random.seed(self.user_id)

        if question_type == "word_cloud":
            answer = self._generate_word_cloud_answer()
        elif question_type == "multiple_choice":
            # Select from available options
            options = self.current_question.get("options", ["A", "B", "C", "D"])
            answer = random.choice(options)
        elif question_type == "fill_in_the_blank":
            # Generate realistic fill-in-the-blank answers
            answers = [
                "Paris", "London", "New York", "Tokyo", "Sydney",
                "Christmas tree", "Team collaboration", "Innovation",
                "Success", "Leadership", "Holiday spirit", "Family time",
                "150", "75", "42", "100", "25"  # Numeric answers
            ]
            answer = random.choice(answers)
        elif question_type == "pictionary":
            # Descriptive answers for drawing questions
            answers = [
                "house", "tree", "car", "dog", "cat", "sun", "moon",
                "mountain", "river", "ocean", "flower", "bird", "fish",
                "Christmas tree", "snowman", "reindeer", "santa claus",
                "gingerbread man", "stocking", "present", "candle"
            ]
            answer = random.choice(answers)
        elif question_type == "wheel_of_fortune":
            # For wheel of fortune, participants guess the full phrase
            # Since we don't know the actual phrase, provide varied guesses
            answers = [
                "merry christmas", "happy holidays", "season greetings",
                "joy to the world", "silent night", "jingle bells",
                "winter wonderland", "holiday cheer", "peace on earth",
                "goodwill toward men", "deck the halls", "we wish you"
            ]
            answer = random.choice(answers)
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
        """Start the load test"""
        print(f"🚀 Starting Interactive Load Test with {self.num_users} users")
        print("Supports all question types: word_cloud, multiple_choice, fill_in_the_blank, pictionary, wheel_of_fortune")
        print("Connect to http://localhost:8000/admin to control the quiz")
        print("Users will join automatically and respond to questions")
        print()

        self.running = True

        # Start status monitoring thread
        self.status_thread = threading.Thread(target=self._monitor_status)
        self.status_thread.daemon = True
        self.status_thread.start()

        # Start all participants
        async def run_all():
            tasks = [p.connect_and_listen() for p in self.participants]
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
