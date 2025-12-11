// All-Hands Quiz Game - Admin Client
class QuizAdmin {
    constructor() {
        this.ws = null;
        this.isAuthenticated = false;
        this.drawingCanvas = null;
        this.isDrawing = false;
        this.lastPos = { x: 0, y: 0 };

        this.init();
    }

    init() {
        this.setupLogin();
        this.updateStatus('Ready to login');
    }

    setupLogin() {
        const loginBtn = document.getElementById('login-btn');
        const passwordInput = document.getElementById('password-input');

        loginBtn.addEventListener('click', () => {
            this.attemptLogin();
        });

        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.attemptLogin();
            }
        });
    }

    attemptLogin() {
        const password = document.getElementById('password-input').value;
        const correctPassword = 'quizmaster2024'; // Hardcoded password

        if (password === correctPassword) {
            this.isAuthenticated = true;
            document.getElementById('login-screen').classList.add('hidden');
            document.getElementById('admin-interface').classList.remove('hidden');
            this.setupWebSocket();
            this.setupAdminControls();
            this.updateStatus('Logged in - Setting up quiz controls');
        } else {
            document.getElementById('login-error').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('login-error').classList.add('hidden');
            }, 3000);
        }
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/admin`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateStatus('Connected to quiz server');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            this.updateStatus('Disconnected from server');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Connection error');
        };
    }

    setupAdminControls() {
        // Quiz controls
        document.getElementById('start-quiz-btn').addEventListener('click', () => {
            this.sendMessage({ type: 'start_quiz' });
        });

        document.getElementById('next-question-btn').addEventListener('click', () => {
            this.sendMessage({ type: 'next_question' });
        });

        document.getElementById('end-quiz-btn').addEventListener('click', () => {
            this.sendMessage({ type: 'end_quiz' });
        });

        // Question setup
        document.getElementById('add-question-btn').addEventListener('click', () => {
            this.addQuestion();
        });

        // Drawing controls
        this.setupDrawingCanvas();
    }

    setupDrawingCanvas() {
        const canvas = document.getElementById('admin-draw-canvas');
        const ctx = canvas.getContext('2d');

        // Set canvas size
        canvas.width = 800;
        canvas.height = 600;

        // Set drawing style
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // Drawing event listeners
        canvas.addEventListener('mousedown', (e) => {
            this.startDrawing(e, canvas);
        });

        canvas.addEventListener('mousemove', (e) => {
            this.draw(e, canvas);
        });

        canvas.addEventListener('mouseup', () => {
            this.stopDrawing();
        });

        canvas.addEventListener('mouseout', () => {
            this.stopDrawing();
        });

        // Touch events for mobile
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            canvas.dispatchEvent(mouseEvent);
        });

        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            canvas.dispatchEvent(mouseEvent);
        });

        canvas.addEventListener('touchend', (e) => {
            const mouseEvent = new MouseEvent('mouseup');
            canvas.dispatchEvent(mouseEvent);
        });

        // Clear button
        document.getElementById('clear-canvas').addEventListener('click', () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });

        // Finish drawing button
        document.getElementById('finish-drawing').addEventListener('click', () => {
            this.sendMessage({ type: 'push_drawing' });
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            document.getElementById('drawing-area').classList.add('hidden');
        });
    }

    startDrawing(e, canvas) {
        this.isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        this.lastPos = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    draw(e, canvas) {
        if (!this.isDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentPos = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };

        const ctx = canvas.getContext('2d');
        ctx.beginPath();
        ctx.moveTo(this.lastPos.x, this.lastPos.y);
        ctx.lineTo(currentPos.x, currentPos.y);
        ctx.stroke();

        // Send stroke to participants
        this.sendMessage({
            type: 'drawing_stroke',
            stroke: {
                from: this.lastPos,
                to: currentPos,
                color: ctx.strokeStyle,
                width: ctx.lineWidth
            }
        });

        this.lastPos = currentPos;
    }

    stopDrawing() {
        this.isDrawing = false;
    }

    addQuestion() {
        const type = document.getElementById('question-type').value;
        const content = document.getElementById('question-content').value.trim();
        const correctAnswer = document.getElementById('correct-answer').value.trim();

        if (!content || !correctAnswer) {
            alert('Please fill in all fields');
            return;
        }

        const question = {
            type: type,
            content: content,
            correct_answer: correctAnswer,
            category: 'general' // Could be expanded
        };

        // For multiple choice, parse options from content
        if (type === 'multiple_choice') {
            // Assume options are separated by newlines in content
            const lines = content.split('\n');
            question.content = lines[0]; // First line is question
            question.options = lines.slice(1).filter(line => line.trim()); // Rest are options
        }

        this.sendMessage({
            type: 'add_question',
            question: question
        });

        // Clear form
        document.getElementById('question-content').value = '';
        document.getElementById('correct-answer').value = '';

        alert('Question added successfully!');
    }

    handleMessage(data) {
        switch (data.type) {
            case 'quiz_started':
                document.getElementById('start-quiz-btn').disabled = true;
                document.getElementById('next-question-btn').disabled = false;
                document.getElementById('end-quiz-btn').disabled = false;
                this.updateStatus('Quiz started');
                break;

            case 'question_pushed':
                document.getElementById('question-text').textContent = data.question.content;
                if (data.question.type === 'drawing') {
                    document.getElementById('drawing-area').classList.remove('hidden');
                }
                break;

            case 'answer_received':
                this.updateAnswersList(data.answers);
                break;

            case 'scores_updated':
                this.updateLeaderboard(data.scores);
                break;

            case 'quiz_ended':
                document.getElementById('start-quiz-btn').disabled = false;
                document.getElementById('next-question-btn').disabled = true;
                document.getElementById('end-quiz-btn').disabled = true;
                this.updateStatus('Quiz ended');
                break;
        }
    }

    updateAnswersList(answers) {
        const container = document.getElementById('answers-list');
        container.innerHTML = '';

        if (answers.length === 0) {
            container.textContent = 'No answers yet...';
            return;
        }

        answers.forEach(answer => {
            const div = document.createElement('div');
            div.className = 'answer-item';
            div.innerHTML = `
                <strong>${answer.user}:</strong> ${answer.content}
                <span class="${answer.correct ? 'correct' : 'incorrect'}">
                    ${answer.correct ? '✓' : '✗'}
                </span>
            `;
            container.appendChild(div);
        });
    }

    updateLeaderboard(scores) {
        const container = document.getElementById('scores-list');
        container.innerHTML = '';

        if (scores.length === 0) {
            container.textContent = 'No scores yet...';
            return;
        }

        scores.forEach((score, index) => {
            const div = document.createElement('div');
            div.className = 'score-item';
            div.innerHTML = `
                <span class="rank">#${index + 1}</span>
                <span class="name">${score.name}</span>
                <span class="points">${score.points} pts</span>
            `;
            container.appendChild(div);
        });
    }

    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected');
        }
    }

    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new QuizAdmin();
});
