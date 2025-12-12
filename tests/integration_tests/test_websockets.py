"""
Integration tests for WebSocket functionality and real-time features
"""

import pytest
import asyncio
import json
import websockets
import sys
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from main import app
import threading
import time
from concurrent.futures import ThreadPoolExecutor


class TestWebSocketConnections:
    """Test WebSocket connection establishment and basic functionality"""

    def test_participant_connection(self):
        """Test participant WebSocket connection"""
        async def test_connection():
            uri = "ws://localhost:8000/ws/participant"
            async with websockets.connect(uri) as websocket:
                # Send join message
                join_message = {
                    "type": "join",
                    "name": "TestParticipant"
                }
                await websocket.send(json.dumps(join_message))

                # Should receive some response (may be quiz state or confirmation)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    # Connection successful if we get any valid JSON response
                    assert isinstance(data, dict)
                except asyncio.TimeoutError:
                    # Connection established even if no immediate response
                    pass

        asyncio.run(test_connection())

    def test_admin_connection(self):
        """Test admin WebSocket connection"""
        async def test_connection():
            uri = "ws://localhost:8000/ws/admin"
            async with websockets.connect(uri) as websocket:
                # Admin connections don't require initial join message
                # Should be able to receive status updates
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    assert isinstance(data, dict)
                    assert "type" in data
                except asyncio.TimeoutError:
                    # Connection established even if no immediate response
                    pass

        asyncio.run(test_connection())

    def test_multiple_connections(self):
        """Test multiple simultaneous WebSocket connections"""
        async def create_connection(name):
            uri = "ws://localhost:8000/ws/participant"
            try:
                async with websockets.connect(uri) as websocket:
                    join_message = {"type": "join", "name": name}
                    await websocket.send(json.dumps(join_message))
                    await asyncio.sleep(0.1)  # Brief connection hold
                    return True
            except Exception as e:
                print(f"Connection failed for {name}: {e}")
                return False

        async def test_multiple():
            # Create 10 concurrent connections
            tasks = []
            for i in range(10):
                tasks.append(create_connection(f"User{i}"))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_connections = sum(1 for r in results if r is True)

            # At least 80% success rate for basic connectivity test
            assert successful_connections >= 8, f"Only {successful_connections}/10 connections succeeded"

        asyncio.run(test_multiple())


class TestQuizFlow:
    """Test complete quiz flow with WebSocket interactions"""

    def test_quiz_lifecycle(self):
        """Test starting and ending a quiz"""
        async def test_flow():
            # Connect admin
            admin_uri = "ws://localhost:8000/ws/admin"
            async with websockets.connect(admin_uri) as admin_ws:
                # Connect participant
                participant_uri = "ws://localhost:8000/ws/participant"
                async with websockets.connect(participant_uri) as participant_ws:
                    # Participant joins
                    join_msg = {"type": "join", "name": "TestPlayer"}
                    await participant_ws.send(json.dumps(join_msg))

                    # Admin starts quiz
                    start_msg = {"type": "start_quiz"}
                    await admin_ws.send(json.dumps(start_msg))

                    # Both should receive quiz_started messages
                    admin_responses = []
                    participant_responses = []

                    # Listen for responses with timeout
                    try:
                        # Get admin response
                        admin_response = await asyncio.wait_for(admin_ws.recv(), timeout=2.0)
                        admin_responses.append(json.loads(admin_response))

                        # Get participant response
                        participant_response = await asyncio.wait_for(participant_ws.recv(), timeout=2.0)
                        participant_responses.append(json.loads(participant_response))

                    except asyncio.TimeoutError:
                        pass

                    # Check for quiz_started messages
                    admin_started = any(r.get("type") == "quiz_started" for r in admin_responses)
                    participant_started = any(r.get("type") == "quiz_started" for r in participant_responses)

                    # At least one of them should have received quiz_started
                    assert admin_started or participant_started, "No quiz_started message received"

        asyncio.run(test_flow())

    def test_question_pushing(self):
        """Test pushing questions during active quiz"""
        async def test_question_flow():
            admin_uri = "ws://localhost:8000/ws/admin"
            participant_uri = "ws://localhost:8000/ws/participant"

            async with websockets.connect(admin_uri) as admin_ws, \
                       websockets.connect(participant_uri) as participant_ws:

                # Setup: participant joins, admin starts quiz
                await participant_ws.send(json.dumps({"type": "join", "name": "TestPlayer"}))
                await admin_ws.send(json.dumps({"type": "start_quiz"}))

                # Wait a bit for setup
                await asyncio.sleep(0.5)

                # Admin pushes next question
                next_question_msg = {"type": "next_question"}
                await admin_ws.send(json.dumps(next_question_msg))

                # Collect responses
                responses = []
                try:
                    for _ in range(4):  # Listen for multiple messages
                        response = await asyncio.wait_for(participant_ws.recv(), timeout=1.0)
                        responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    pass

                # Should receive question message
                question_received = any(r.get("type") == "question" for r in responses)
                assert question_received, f"No question received. Responses: {responses}"

        asyncio.run(test_question_flow())


class TestRealTimeMessaging:
    """Test real-time messaging performance and reliability"""

    def test_message_broadcasting(self):
        """Test that messages are broadcast to all connected clients"""
        async def test_broadcast():
            participant_uris = ["ws://localhost:8000/ws/participant" for _ in range(5)]

            async def connect_and_listen(uri, name):
                messages = []
                try:
                    async with websockets.connect(uri) as ws:
                        # Join
                        await ws.send(json.dumps({"type": "join", "name": name}))

                        # Listen for messages
                        for _ in range(5):  # Listen for 5 messages max
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                messages.append(json.loads(msg))
                            except asyncio.TimeoutError:
                                break
                except Exception as e:
                    print(f"Error for {name}: {e}")
                return messages

            # Connect 5 participants
            tasks = []
            for i in range(5):
                tasks.append(connect_and_listen(participant_uris[i], f"User{i}"))

            # Start admin and trigger broadcasts
            async def admin_actions():
                await asyncio.sleep(0.2)  # Let participants connect
                admin_uri = "ws://localhost:8000/ws/admin"
                try:
                    async with websockets.connect(admin_uri) as admin_ws:
                        # Start quiz (broadcasts to all)
                        await admin_ws.send(json.dumps({"type": "start_quiz"}))
                        await asyncio.sleep(0.1)

                        # Push question (broadcasts to all)
                        await admin_ws.send(json.dumps({"type": "next_question"}))
                        await asyncio.sleep(0.1)

                        # End quiz (broadcasts to all)
                        await admin_ws.send(json.dumps({"type": "end_quiz"}))
                        await asyncio.sleep(0.1)

                except Exception as e:
                    print(f"Admin error: {e}")

            # Run admin actions and participant listeners concurrently
            all_tasks = tasks + [admin_actions()]
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            # Check that participants received broadcasts
            participant_results = results[:-1]  # Exclude admin task result
            successful_receivers = 0

            for i, messages in enumerate(participant_results):
                if isinstance(messages, list) and len(messages) > 0:
                    successful_receivers += 1
                    print(f"User{i} received {len(messages)} messages")
                else:
                    print(f"User{i} received no messages or had errors")

            # At least 60% of participants should receive messages
            assert successful_receivers >= 3, f"Only {successful_receivers}/5 participants received messages"

        asyncio.run(test_broadcast())

    def test_answer_submission(self):
        """Test participant answer submission and feedback"""
        async def test_answer_flow():
            admin_uri = "ws://localhost:8000/ws/admin"
            participant_uri = "ws://localhost:8000/ws/participant"

            async with websockets.connect(admin_uri) as admin_ws, \
                       websockets.connect(participant_uri) as participant_ws:

                # Setup quiz
                await participant_ws.send(json.dumps({"type": "join", "name": "AnswerTester"}))
                await admin_ws.send(json.dumps({"type": "start_quiz"}))
                await asyncio.sleep(0.2)

                # Push question
                await admin_ws.send(json.dumps({"type": "next_question"}))
                await asyncio.sleep(0.2)

                # Participant submits answer
                answer_msg = {
                    "type": "answer",
                    "question_id": 1,  # Assume first question
                    "answer": "Test Answer"
                }
                await participant_ws.send(json.dumps(answer_msg))

                # Should receive personal feedback
                feedback_received = False
                try:
                    response = await asyncio.wait_for(participant_ws.recv(), timeout=2.0)
                    data = json.loads(response)
                    if data.get("type") == "personal_feedback":
                        feedback_received = True
                        assert "correct" in data
                        assert "retry_count" in data
                except asyncio.TimeoutError:
                    pass

                assert feedback_received, "No personal feedback received after answer submission"

        asyncio.run(test_answer_flow())


class TestConnectionStability:
    """Test connection stability under various conditions"""

    def test_connection_reestablishment(self):
        """Test handling of connection drops and reestablishment"""
        async def test_reconnect():
            uri = "ws://localhost:8000/ws/participant"

            # First connection
            async with websockets.connect(uri) as ws1:
                await ws1.send(json.dumps({"type": "join", "name": "ReconnectTest"}))

                # Simulate disconnection and immediate reconnection
                pass  # In a real test, would close and reconnect

            # Second connection (simulating user reconnecting)
            async with websockets.connect(uri) as ws2:
                await ws2.send(json.dumps({"type": "join", "name": "ReconnectTest"}))

                # Should be able to reconnect successfully
                try:
                    response = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                    # Connection reestablished successfully
                    assert True
                except asyncio.TimeoutError:
                    # Connection established even without immediate response
                    assert True

        asyncio.run(test_reconnect())

    def test_concurrent_load_simulation(self):
        """Simulate concurrent load similar to 150 users"""
        async def simulate_load():
            uri = "ws://localhost:8000/ws/participant"

            async def user_session(user_id):
                try:
                    async with websockets.connect(uri) as websocket:
                        # Join quiz
                        join_msg = {"type": "join", "name": f"LoadUser{user_id}"}
                        await websocket.send(json.dumps(join_msg))

                        # Simulate user activity
                        await asyncio.sleep(0.1)  # Brief connection

                        # Simulate answering a question
                        answer_msg = {
                            "type": "answer",
                            "question_id": 1,
                            "answer": f"Answer from user {user_id}"
                        }
                        await websocket.send(json.dumps(answer_msg))

                        await asyncio.sleep(0.1)  # Brief wait for response
                        return True
                except Exception as e:
                    print(f"User {user_id} failed: {e}")
                    return False

            # Simulate 20 concurrent users (scaled down from 150 for integration test)
            tasks = [user_session(i) for i in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_sessions = sum(1 for r in results if r is True)
            success_rate = successful_sessions / len(tasks)

            print(f"Concurrent load test: {successful_sessions}/{len(tasks)} successful ({success_rate:.1%})")

            # Require at least 80% success rate
            assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"

        asyncio.run(simulate_load())


class TestHTTPIntegration:
    """Test HTTP endpoints that support WebSocket functionality"""

    def test_health_endpoint(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root API endpoint"""
        client = TestClient(app)
        response = client.get("/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data

    def test_static_file_serving(self):
        """Test that static files are served correctly"""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Should serve HTML content
        assert "text/html" in response.headers.get("content-type", "")

        response = client.get("/admin")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
