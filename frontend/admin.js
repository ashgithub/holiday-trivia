// All-Hands Quiz Game - Admin Client
class QuizAdmin {
    constructor() {
        this.ws = null;
        this.isAuthenticated = false;
        this.drawingCanvas = null;
        this.isDrawing = false;
        this.lastPos = { x: 0, y: 0 };
        this.questions = [];
        this.currentTab = 'quiz-control';

        this.init();
    }

    init() {
        this.setupLogin();
        this.setupTabs();
        this.updateStatus('Ready to login');
    }

    setupTabs() {
        // Tab switching
        document.getElementById('quiz-control-tab').addEventListener('click', () => {
            this.switchTab('quiz-control');
        });

        document.getElementById('question-management-tab').addEventListener('click', () => {
            this.switchTab('question-management');
        });

        document.getElementById('settings-tab').addEventListener('click', () => {
            this.switchTab('settings');
        });

        // Settings
        document.getElementById('save-settings-btn').addEventListener('click', () => {
            this.saveSettings();
        });
    }

    switchTab(tabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // Add active class to selected tab
        document.getElementById(`${tabName}-tab`).classList.add('active');
        document.getElementById(`${tabName}-content`).classList.add('active');

        this.currentTab = tabName;
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
        const correctPassword = 'quizzer'; // Hardcoded password

        if (password === correctPassword) {
            this.isAuthenticated = true;

            const loginScreen = document.getElementById('login-screen');
            const adminInterface = document.getElementById('admin-interface');

            loginScreen.classList.add('hidden');
            adminInterface.classList.remove('hidden');



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

        // Load existing questions
        this.loadQuestions();

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
            case 'status_update':
                this.updateStatusDashboard(data);
                break;

            case 'quiz_started':
                document.getElementById('start-quiz-btn').disabled = true;
                document.getElementById('next-question-btn').disabled = false;
                document.getElementById('end-quiz-btn').disabled = false;
                this.updateStatus('Quiz started');
                break;

            case 'question_pushed':
                document.getElementById('question-text').textContent = data.question.content;
                if (data.progress) {
                    document.getElementById('admin-question-progress').textContent = `Question ${data.progress.current} of ${data.progress.total}`;
                    // Disable next-question button if we've reached the final question
                    if (data.progress.current >= data.progress.total) {
                        document.getElementById('next-question-btn').disabled = true;
                    } else {
                        document.getElementById('next-question-btn').disabled = false;
                    }
                }
                // Reset answer counter for new question - show 0 answered (0 correct)
                const currentParticipantCount = parseInt(document.getElementById('participant-count').textContent) || 0;
                document.getElementById('answer-counter').textContent = `0 answered (0 correct) out of ${currentParticipantCount} participants`;
                if (data.question.type === 'drawing') {
                    document.getElementById('drawing-area').classList.remove('hidden');
                }
                break;

            case 'timer_update':
                document.getElementById('admin-time-remaining').textContent = data.time_left;
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

            case 'questions_loaded':
                this.updateQuestionsList(data.questions);
                break;

            case 'question_added':
                this.loadQuestions(); // Refresh the question list
                break;

            case 'question_deleted':
                this.loadQuestions(); // Refresh the question list
                break;
        }
    }

    updateAnswersList(answers) {
        const tbody = document.getElementById('answers-tbody');
        tbody.innerHTML = '';

        const participantCount = parseInt(document.getElementById('participant-count').textContent) || 0;

        if (answers.length === 0) {
            const row = tbody.insertRow();
            row.className = 'no-answers';
            const cell = row.insertCell();
            cell.colSpan = 4;
            cell.textContent = 'Waiting for answers...';
            // Update counter to correct format
            document.getElementById('answer-counter').textContent = `0 answered (0 correct) out of ${participantCount} participants`;
            return;
        }

        // Calculate counts
        const totalAnswered = answers.length;
        const correctCount = answers.filter(answer => answer.correct).length;

        // Update counter with both counts
        document.getElementById('answer-counter').textContent = `${totalAnswered} answered (${correctCount} correct) out of ${participantCount} participants`;

        // Sort answers by timestamp (newest first)
        answers.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        answers.forEach(answer => {
            const row = tbody.insertRow();

            // Time column
            const timeCell = row.insertCell();
            timeCell.className = 'time';
            timeCell.textContent = new Date(answer.timestamp).toLocaleTimeString();

            // Participant column
            const participantCell = row.insertCell();
            participantCell.textContent = answer.user;

            // Answer column
            const answerCell = row.insertCell();
            answerCell.textContent = answer.content;

            // Status column
            const statusCell = row.insertCell();
            statusCell.className = answer.correct ? 'correct' : 'incorrect';
            statusCell.textContent = answer.correct ? '✓ Correct' : '✗ Incorrect';
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

    updateStatusDashboard(data) {
        // Update participant count
        const oldCount = parseInt(document.getElementById('participant-count').textContent) || 0;
        document.getElementById('participant-count').textContent = data.participant_count;

        // Update answer counter if participant count changed and we have answers
        if (oldCount !== data.participant_count) {
            this.updateAnswerCounter();
        }

        // Update quiz status
        const quizStatus = data.quiz_active ? 'Active' : 'Waiting';
        document.getElementById('quiz-status').textContent = quizStatus;

        // Update current question status
        const questionStatus = data.current_question ?
            (data.current_question.length > 20 ?
                data.current_question.substring(0, 20) + '...' :
                data.current_question) :
            'None';
        document.getElementById('current-question-status').textContent = questionStatus;

        // Update answered and correct answers count if available
        if (data.hasOwnProperty('total_answered') && data.hasOwnProperty('correct_answers')) {
            const participantCount = data.participant_count;
            const totalAnswered = data.total_answered || 0;
            const correctCount = data.correct_answers || 0;
            document.getElementById('answer-counter').textContent = `${totalAnswered} answered (${correctCount} correct) out of ${participantCount} participants`;
        }
    }

    updateAnswerCounter() {
        // Get current answered and correct counts from table
        const tbody = document.getElementById('answers-tbody');
        const rows = tbody.querySelectorAll('tr:not(.no-answers)');
        const totalAnswered = rows.length;
        const correctCount = Array.from(rows).filter(row => row.querySelector('.correct')).length;

        // Get current participant count
        const participantCount = parseInt(document.getElementById('participant-count').textContent) || 0;

        // Update counter
        document.getElementById('answer-counter').textContent = `${totalAnswered} answered (${correctCount} correct) out of ${participantCount} participants`;
    }

    loadQuestions() {
        // Send request to load existing questions
        this.sendMessage({ type: 'get_questions' });
    }

    updateQuestionsList(questions) {
        const container = document.getElementById('questions-list');
        container.innerHTML = '';

        if (!questions || questions.length === 0) {
            container.textContent = 'No questions added yet...';
            return;
        }

        questions.forEach((question, index) => {
            const div = document.createElement('div');
            div.className = 'question-item';
            div.innerHTML = `
                <div class="question-header">
                    <strong>${question.type.replace('_', ' ').toUpperCase()}</strong>
                    <button class="btn btn-danger btn-small delete-btn" data-index="${index}">Delete</button>
                </div>
                <div class="question-content">${question.content}</div>
                <div class="question-answer">Answer: ${question.correct_answer}</div>
            `;
            container.appendChild(div);
        });

        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.deleteQuestion(index);
            });
        });
    }

    deleteQuestion(index) {
        if (confirm('Are you sure you want to delete this question?')) {
            this.sendMessage({
                type: 'delete_question',
                index: index
            });
        }
    }

    saveSettings() {
        const questionTimer = parseInt(document.getElementById('question-timer').value);
        const maxParticipants = parseInt(document.getElementById('max-participants').value);

        if (questionTimer < 10 || questionTimer > 120) {
            alert('Question timer must be between 10 and 120 seconds');
            return;
        }

        if (maxParticipants < 1 || maxParticipants > 500) {
            alert('Max participants must be between 1 and 500');
            return;
        }

        this.sendMessage({
            type: 'save_settings',
            settings: {
                question_timer: questionTimer,
                max_participants: maxParticipants
            }
        });

        alert('Settings saved successfully!');
    }

    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new QuizAdmin();
});
