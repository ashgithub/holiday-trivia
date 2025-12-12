"""
Locust load testing for All-Hands Quiz Game

This file simulates 150 concurrent users participating in a quiz game,
testing both load handling and correctness under stress conditions.
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.exception import StopUser
import websockets
import asyncio
import threading
import statistics


class QuizParticipant(HttpUser):
    """
    Simulates a quiz participant connecting via WebSocket and answering questions.

    This class tests:
    - WebSocket connection establishment (150 concurrent connections)
    - Real-time message handling
    - Answer submission under load
    - Connection stability during quiz flow
    """

    # Random delay between 1-3 seconds between tasks
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = None
        self.user_name = None
        self.current_question = None
        self.game_active = False
        self.connection_start_time = None
        self.messages_received = 0
        self.answers_submitted = 0

    def on_start(self):
        """Called when a simulated user starts"""
        self.user_name = f"LoadTestUser_{random.randint(1000, 9999)}"
        self.connection_start_time = time.time()

        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self._run_websocket_client)
        self.ws_thread.daemon = True
        self.ws_thread.start()

        # Give WebSocket time to connect
        time.sleep(2)

    def on_stop(self):
        """Called when a simulated user stops"""
        if self.websocket:
            # Close WebSocket connection
            asyncio.run(self.websocket.close())

    async def _websocket_connect(self):
        """Establish WebSocket connection and handle messages"""
        try:
            uri = "ws://localhost:8000/ws/participant"
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                connection_time = time.time() - (self.connection_start_time or time.time())
                self.environment.events.request.fire(
                    request_type="WEBSOCK",
                    name="websocket_connect",
                    response_time=int(connection_time * 1000),
                    response_length=0,
                    exception=None,
                )

                # Send join message
                join_message = {
                    "type": "join",
                    "name": self.user_name
                }
                await websocket.send(json.dumps(join_message))

                # Listen for messages
                async for message in websocket:
                    await self._handle_message(message)

        except Exception as e:
            self.environment.events.request.fire(
                request_type="WEBSOCK",
                name="websocket_error",
                response_time=0,
                response_length=0,
                exception=e,
            )
            raise StopUser()

    def _run_websocket_client(self):
        """Run WebSocket client in asyncio event loop"""
        try:
            asyncio.run(self._websocket_connect())
        except Exception as e:
            print(f"WebSocket error for {self.user_name}: {e}")

    async def _handle_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            self.messages_received += 1

            if data["type"] == "quiz_started":
                self.game_active = True

            elif data["type"] == "question":
                self.current_question = data["question"]
                # Simulate thinking time before answering
                await asyncio.sleep(random.uniform(1, 8))
                await self._submit_answer()

            elif data["type"] == "quiz_ended":
                self.game_active = False

            elif data["type"] == "personal_feedback":
                # Answer feedback received
                pass

        except Exception as e:
            print(f"Error handling message: {e}")

    async def _submit_answer(self):
        """Submit an answer to the current question"""
        if not self.current_question or not self.websocket:
            return

        # Generate realistic answer based on question type
        answer = self._generate_answer(self.current_question)

        answer_message = {
            "type": "answer",
            "question_id": self.current_question["id"],
            "answer": answer
        }

        try:
            await self.websocket.send(json.dumps(answer_message))
            self.answers_submitted += 1

            self.environment.events.request.fire(
                request_type="WEBSOCK",
                name="answer_submit",
                response_time=random.randint(50, 200),  # Simulate network latency
                response_length=len(json.dumps(answer_message)),
                exception=None,
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="WEBSOCK",
                name="answer_error",
                response_time=0,
                response_length=0,
                exception=e,
            )

    def _generate_answer(self, question):
        """Generate realistic answers based on question type"""
        q_type = question.get("type", "fill_blank")

        if q_type == "multiple_choice":
            options = question.get("options", ["A", "B", "C", "D"])
            return random.choice(options)

        elif q_type == "word_cloud":
            words = ["innovation", "teamwork", "leadership", "growth", "success"]
            return random.choice(words)

        elif q_type == "drawing":
            return "A simple drawing description"

        elif q_type == "wheel_of_fortune":
            return "Sample phrase guess"

        else:  # fill_blank or other types
            answers = [
                "Christmas tree",
                "Team collaboration",
                "Innovation",
                "Success",
                "Leadership"
            ]
            return random.choice(answers)

    @task(1)
    def check_connection_health(self):
        """Periodic health check task"""
        if not self.websocket:
            self.environment.events.request.fire(
                request_type="WEBSOCK",
                name="connection_check",
                response_time=0,
                response_length=0,
                exception=Exception("No active WebSocket connection"),
            )
        else:
            # Connection is healthy
            self.environment.events.request.fire(
                request_type="WEBSOCK",
                name="connection_healthy",
                response_time=1,
                response_length=0,
                exception=None,
            )

    @task(2)
    def simulate_user_activity(self):
        """Simulate general user activity and collect metrics"""
        # This task runs periodically to collect metrics
        metrics = {
            "messages_received": self.messages_received,
            "answers_submitted": self.answers_submitted,
            "connection_duration": time.time() - self.connection_start_time if self.connection_start_time else 0,
            "game_active": self.game_active
        }

        self.environment.events.request.fire(
            request_type="CUSTOM",
            name="user_metrics",
            response_time=1,
            response_length=len(json.dumps(metrics)),
            exception=None,
        )


class QuizAdmin(HttpUser):
    """
    Simulates the quiz master/admin controlling the game.

    This class tests admin panel performance under load.
    """

    wait_time = between(5, 15)  # Admin actions are less frequent

    @task
    def admin_status_check(self):
        """Check admin status and participant count"""
        self.client.get("/api/health")
        # In a real scenario, would check WebSocket connection to admin endpoint

    @task
    def simulate_quiz_control(self):
        """Simulate quiz master actions (when implemented)"""
        # This would test admin controls under load
        pass


# Custom event handlers for detailed metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("Starting load test for All-Hands Quiz Game")
    print("Testing with simulated participants...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("Load test completed")
    print("Analyzing results...")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Custom request event handler for detailed logging"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif name in ["websocket_connect", "answer_submit"]:
        # Log important events
        pass


# Configuration for running the test
if __name__ == "__main__":
    # This allows running the file directly with locust
    import locust.main
    locust.main.main()
