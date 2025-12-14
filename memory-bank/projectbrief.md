# Project Brief: All-Hands Quiz Game

## Background
This project creates an interactive quiz game for all-hands meetings conducted over Zoom (web conferencing). Approximately 150 individuals will participate, playing the game in real-time.

## Roles
1. **Quiz Master**: One person acting as the quiz master. The quiz master shares their screen and pushes questions to participants.
2. **Participants**: Everyone other than the quiz master is a participant. They view questions pushed to their screens, respond, and see responses pushed back to the quiz master for real-time scoring.

## Questions
The system supports comprehensive question libraries with 25+ questions across 4 categories (Geography, Science, History, General). Questions are dynamically managed through the admin interface.

**Supported Question Types:**
1. **Fill in the Blank**: A sentence with missing words. Participants fill in the word. The quiz master's screen shows guesses with participant names. The matching answer wins.

2. **Word Cloud**: Quiz master provides a prompt. Participants respond with 1-3 word phrases. The quiz master's screen forms a word cloud. Words matching the most popular responses win.

3. **Drawing**: The quiz master draws a phrase. Participants see the drawing being created in real-time and guess. Guesses appear on the screen. Participants can make multiple guesses. The nearest match wins.

4. **Wheel of Fortune**: The quiz master selects a phrase and a category. During this round:
   - Both admin and participants see a prompt: “Guess the phrase in <category>.”
   - The phrase is displayed as blank tiles; the answer is revealed letter-by-letter (one tile at a time) at a pace determined by a configurable tile duration (e.g., 2 seconds per letter).
   - Participants guess the **full phrase** at any time as tiles are revealed (no per-letter guessing, no spinning or randomness).
   - Multiple attempts are allowed during the reveal.
   - The round ends when a participant guesses correctly or the full phrase is revealed.

5. **Multiple Choice**: Quiz master pushes a question with 4 answers. Participants choose one or more answers.

The quiz master can configure questions beforehand via a UI page for entering questions and answers. Questions are pushed in real-time on demand. Participant answers appear on the quiz master's screen, sorted by time and correctness. The scoreboard shows winners.

## Answers
Participants can type answers or speak. Browser-native voice-to-text converts speech to text. Pressing Enter sends responses. Some question types allow only one correct attempt. Drawing and Wheel of Fortune allow multiple full-phrase guesses during the round.

## Scoring
Correct guesses win a point. The leaderboard shows top winners. Ties are decided by the quiz master.

## Technical Stack
- Pure Python, HTML, JS, CSS application
- Frontend in pure JS, HTML, CSS with WebSocket connections to Python backend using FastAPI
- Real-time communication via WebSockets for instant interaction
- Theme: Christmas with a subtle Christmas background
- Database: SQLite with SQLAlchemy ORM
- Testing: Comprehensive load testing infrastructure for 150 concurrent users

## Gameplay
- Quiz master shares screen
- Clicks "Start Quiz" button
- Screen displays 1 of 10 questions
- Quiz master presses "Push Question" button
- Participant screens display the question and timer starts

**Wheel of Fortune gameplay:**
- The admin and participants see a prompt indicating the category and blank tiles for the phrase.
- Each letter (tile) of the phrase is revealed automatically in sequence, at a set interval.
- Participants may guess the phrase at any time (multiple attempts allowed), submitting their guess while the reveal is ongoing.
- The round ends with a win on a correct guess, or proceeds until the full phrase is revealed.

Answers come in and are evaluated on the quiz master's screen as usual.

Participant screen starts with a welcome screen saying "Waiting for questions". Once a question is received, it resets the timer and allows the participant to answer by typing or speaking.
