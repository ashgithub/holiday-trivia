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
        document.getElementById('name-entry-screen').classList.add('hidden');
        document.getElementById('participant-screen').classList.remove('hidden');

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
                this.displayQuestion(data.question);
                break;

            case 'drawing_start':
                this.showDrawingCanvas();
                break;

            case 'drawing_update':
                this.updateDrawing(data.stroke);
                break;

            case 'timer_update':
                this.updateTimer(data.time_left);
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
        this.updateStatus('Quiz ended - Thanks for playing!');
    }

    displayQuestion(question) {
        this.currentQuestion = question;
        document.getElementById('question-content').textContent = question.content;

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

        const answerText = answer || document.getElementById('text-answer').value.trim();
        if (!answerText) return;

        const message = {
            type: 'answer',
            question_id: this.currentQuestion.id,
            answer: answerText
        };

        this.ws.send(JSON.stringify(message));

        // Clear input
        document.getElementById('text-answer').value = '';

        // For single-attempt questions, disable input
        if (!this.currentQuestion.allow_multiple) {
            document.getElementById('text-answer').disabled = true;
            document.getElementById('submit-btn').disabled = true;
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
                this.submitAnswer(); // Auto-submit empty answer
            }
        }, 1000);
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
