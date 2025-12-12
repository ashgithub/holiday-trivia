// All-Hands Quiz Game - Participant Client
class QuizParticipant {
    constructor() {
        this.ws = null;
        this.currentQuestion = null;
        this.timer = null;
        this.timeLeft = 30;
        this.recognition = null;
        this.isListening = false;
        this.participantName = null;
        this.hasSubmitted = false; // Track if participant has submitted answer

        this.init();
    }

    init() {
        this.setupNameEntry();
        this.setupVoiceRecognition();
        this.updateStatus('Ready to join quiz');
    }

    setupNameEntry() {
        const joinBtn = document.getElementById('join-btn');
        const nameInput = document.getElementById('participant-name');

        joinBtn.addEventListener('click', () => {
            this.attemptJoin();
        });

        nameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.attemptJoin();
            }
        });
    }

    attemptJoin() {
        const name = document.getElementById('participant-name').value.trim();
        const errorDiv = document.getElementById('name-error');

        if (!name) {
            errorDiv.classList.remove('hidden');
            return;
        }

        errorDiv.classList.add('hidden');
        this.participantName = name;


        // Hide name entry, show quiz interface
        const nameEntryScreen = document.getElementById('name-entry-screen');
        const participantScreen = document.getElementById('participant-screen');

        nameEntryScreen.classList.add('hidden');
        participantScreen.classList.remove('hidden');



        // Now connect to WebSocket
        this.setupWebSocket();
        this.setupEventListeners();
        this.updateStatus('Connecting to quiz server...');
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/participant`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            // Send join message with participant name
            this.ws.send(JSON.stringify({
                type: 'join',
                name: this.participantName
            }));
            this.updateStatus('Connected - Waiting for quiz to start');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            this.updateStatus('Disconnected - Refresh page to reconnect');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Connection error');
        };
    }

    setupEventListeners() {
        // Text input
        document.getElementById('text-answer').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.submitAnswer();
            }
        });

        // Submit button
        document.getElementById('submit-btn').addEventListener('click', () => {
            this.submitAnswer();
        });

        // Voice button
        document.getElementById('voice-btn').addEventListener('click', () => {
            this.toggleVoiceRecognition();
        });
    }

    setupVoiceRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('text-answer').value = transcript;
                this.isListening = false;
                this.updateVoiceButton();
            };

            this.recognition.onend = () => {
                this.isListening = false;
                this.updateVoiceButton();
            };

            this.recognition.onerror = (error) => {
                console.error('Speech recognition error:', error);
                this.isListening = false;
                this.updateVoiceButton();
            };
        } else {
            document.getElementById('voice-btn').style.display = 'none';
        }
    }

    toggleVoiceRecognition() {
        if (!this.recognition) return;

        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.start();
            this.isListening = true;
            this.updateVoiceButton();
        }
    }

    updateVoiceButton() {
        const btn = document.getElementById('voice-btn');
        if (this.isListening) {
            btn.textContent = '🎤 Listening...';
            btn.classList.add('listening');
        } else {
            btn.textContent = '🎤 Voice';
            btn.classList.remove('listening');
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'quiz_started':
                this.showQuestionContainer();
                break;

            case 'question':
                this.displayQuestion(data.question, data.progress);
                break;

            case 'drawing_start':
                this.showDrawingCanvas();
                break;

            case 'drawing_update':
                this.updateDrawing(data.stroke);
                break;

            case 'timer_update':
                // Only update timer if question is still active (timeLeft > 0) and participant hasn't submitted
                if (this.timeLeft > 0 && !this.hasSubmitted) {
                    this.updateTimer(data.time_left);
                }
                break;

            case 'quiz_ended':
                this.showWaitingMessage();
                break;
        }
    }

    showQuestionContainer() {
        document.getElementById('waiting-message').classList.add('hidden');
        document.getElementById('question-container').classList.remove('hidden');
        document.getElementById('drawing-canvas').classList.add('hidden');
    }

    showDrawingCanvas() {
        document.getElementById('waiting-message').classList.add('hidden');
        document.getElementById('question-container').classList.add('hidden');
        document.getElementById('drawing-canvas').classList.remove('hidden');
    }

    showWaitingMessage() {
        document.getElementById('question-container').classList.add('hidden');
        document.getElementById('drawing-canvas').classList.add('hidden');
        document.getElementById('waiting-message').classList.remove('hidden');
        document.getElementById('waiting-message').innerHTML = `
            <h2>Quiz Finished!</h2>
            <p>Thanks for playing! The quiz has ended.</p>
            <div class="snowflake">🎉</div>
        `;
        this.updateStatus('Quiz ended - Thanks for playing!');
    }

    displayQuestion(question, progress) {
        this.currentQuestion = question;
        this.hasSubmitted = false; // Reset submission flag for new question

        // Restore timer markup for new question
        document.getElementById('timer').innerHTML = 'Time remaining: <span id="time-remaining">30</span>s';

        // Set default values for missing properties
        if (this.currentQuestion.allow_multiple === undefined) {
            this.currentQuestion.allow_multiple = true; // Default to allowing multiple attempts
        }

        // Update progress display
        if (progress) {
            document.getElementById('question-progress').textContent = `Question ${progress.current} of ${progress.total}`;
        }

        document.getElementById('question-content').textContent = question.content;

        // Re-enable input fields for new question
        const textAnswer = document.getElementById('text-answer');
        const submitBtn = document.getElementById('submit-btn');

        textAnswer.disabled = false;
        textAnswer.value = ''; // Clear any previous answer
        submitBtn.disabled = false;

        // Handle different question types
        if (question.type === 'multiple_choice') {
            this.showMultipleChoice(question.options);
        } else {
            this.hideMultipleChoice();
        }

        this.resetTimer();
    }

    showMultipleChoice(options) {
        const container = document.getElementById('multiple-choice-options');
        container.innerHTML = '';
        container.classList.remove('hidden');

        options.forEach((option, index) => {
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.textContent = option;
            btn.onclick = () => this.selectChoice(index, option);
            container.appendChild(btn);
        });
    }

    hideMultipleChoice() {
        document.getElementById('multiple-choice-options').classList.add('hidden');
    }

    selectChoice(index, text) {
        // Remove previous selection
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.classList.remove('selected');
        });

        // Select current
        event.target.classList.add('selected');

        // Submit answer
        this.submitAnswer(text);
    }

    submitAnswer(answer) {
        if (!this.currentQuestion) return;

        // Check if time has expired
        if (this.timeLeft <= 0) {
            alert('Time has expired! You cannot submit answers after the timer runs out.');
            return;
        }

        const answerText = answer || document.getElementById('text-answer').value.trim();
        if (!answerText) return;

        const message = {
            type: 'answer',
            question_id: this.currentQuestion.id,
            answer: answerText
        };

        this.ws.send(JSON.stringify(message));
        this.hasSubmitted = true; // Mark as submitted

        // Stop the timer
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }

        // Show submitted answer feedback
        const textAnswer = document.getElementById('text-answer');
        const submitBtn = document.getElementById('submit-btn');

        // Update input to show submitted answer
        textAnswer.value = answerText;
        textAnswer.disabled = true;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Answer Submitted';

        // Update timer display to show submission
        document.getElementById('timer').innerHTML = 'Time remaining: Submitted';

        // For single-attempt questions, keep disabled
        if (!this.currentQuestion.allow_multiple) {
            // Already disabled above
        }
    }

    resetTimer() {
        this.timeLeft = 30;
        this.updateTimerDisplay();
        if (this.timer) clearInterval(this.timer);

        this.timer = setInterval(() => {
            this.timeLeft--;
            this.updateTimerDisplay();

            if (this.timeLeft <= 0) {
                clearInterval(this.timer);
                this.timeExpired();
            }
        }, 1000);
    }

    timeExpired() {
        // Disable input fields when time expires
        const textAnswer = document.getElementById('text-answer');
        const submitBtn = document.getElementById('submit-btn');
        const voiceBtn = document.getElementById('voice-btn');

        textAnswer.disabled = true;
        textAnswer.value = 'Time Expired - No answer submitted';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Time Expired';
        voiceBtn.disabled = true;

        // Disable multiple choice buttons if they exist
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });
    }

    updateTimerDisplay() {
        document.getElementById('time-remaining').textContent = this.timeLeft;
    }

    updateTimer(timeLeft) {
        this.timeLeft = timeLeft;
        this.updateTimerDisplay();
    }

    updateDrawing(stroke) {
        const canvas = document.getElementById('draw-canvas');
        const ctx = canvas.getContext('2d');

        ctx.beginPath();
        ctx.moveTo(stroke.from.x, stroke.from.y);
        ctx.lineTo(stroke.to.x, stroke.to.y);
        ctx.strokeStyle = stroke.color || '#000000';
        ctx.lineWidth = stroke.width || 2;
        ctx.stroke();
    }

    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new QuizParticipant();
});
