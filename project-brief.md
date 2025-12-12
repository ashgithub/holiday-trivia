# Project Brief: All-Hands Quiz Game

## Background
This project creates an interactive quiz game for all-hands meetings conducted over Zoom (web conferencing). Approximately 150 individuals will participate, playing the game in real-time.

## Roles
1. **Quiz Master**: One person acting as the quiz master. The quiz master shares their screen and pushes questions to participants.
2. **Participants**: Everyone other than the quiz master is a participant. They view questions pushed to their screens, respond, and see responses pushed back to the quiz master for real-time scoring.

## Questions
There are 10 questions across 5 categories, with each category containing 2 questions.

1. **Fill in the Blank**: A sentence with missing words. Participants fill in the word. The quiz master's screen shows guesses with participant names. The matching answer wins.

2. **Word Cloud**: Quiz master provides a prompt. Participants respond with 1-3 word phrases. The quiz master's screen forms a word cloud. Words matching the most popular responses win.

3. **Drawing**: The quiz master draws a phrase. Participants see the drawing being created in real-time and guess. Guesses appear on the screen. Participants can make multiple guesses. The nearest match wins.

4. **Wheel of Fortune**: Quiz master selects a phrase. Participants see empty tiles as placeholders. One tile from the phrase appears at a time, every 2 seconds. Participants guess the phrase.

5. **Multiple Choice**: Quiz master pushes a question with 4 answers. Participants choose one or more answers.

The quiz master can configure questions beforehand via a UI page for entering questions and answers. Questions are pushed in real-time on demand. Participant answers appear on the quiz master's screen, sorted by time and correctness. The scoreboard shows winners.

## Answers
Participants can type answers or speak. Browser-native voice-to-text converts speech to text. Pressing Enter sends responses. Some question types allow only one correct attempt. Drawing and Wheel of Fortune allow multiple guesses.

## Scoring
Time-based scoring: Correct answers receive points equal to the number of seconds remaining when answered (0-30 points). Incorrect answers receive 0 points. Scores accumulate across all questions. The leaderboard shows cumulative scores with top winners displayed. Ties are decided outside the app.

## Technical Stack
- Pure Python, HTML, JS, CSS application
- Frontend in pure JS, HTML, CSS calling REST APIs on Python backend implemented using FastAPI
- Theme: Christmas with a subtle Christmas background
- Questions and answers handled using HTTP streaming (WebSockets)

## Gameplay
- Quiz master shares screen
- Clicks "Start Quiz" button
- Screen displays 1 of 10 questions
- Quiz master presses "Push Question" button
- Participant screens display the question and timer starts
- Answers come in and are evaluated on the quiz master's screen

Participant screen starts with a welcome screen saying "Waiting for questions". Once a question is received, it resets the timer and allows the participant to answer the question by typing or speaking.

## Additional Considerations
- **Scalability**: Support for up to 150 concurrent participants
- **Real-time Requirements**: Low-latency communication for live drawing and instant responses
- **Browser Compatibility**: Modern browsers with WebSocket and Web Speech API support
- **Deployment**: Web-based application accessible via URL during Zoom meetings
