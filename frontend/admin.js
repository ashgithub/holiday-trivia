// All-Hands Quiz Game - Admin Client
class QuizAdmin {
    constructor() {
        this.ws = null;
        this.isAuthenticated = false;
        this.questions = [];
        this.editingQuestionIndex = undefined;
        this.currentTab = 'quiz-control';

        // Drawing state
        this.drawing = {
            isDrawing: false,
            lastPos: { x: 0, y: 0 },
            canvas: null,
            ctx: null
        };

        // Quiz state
        this.quizState = {
            active: false,
            currentQuestion: null,
            participantCount: 0,
            totalAnswered: 0,
            correctAnswers: 0
        };

        // DOM element cache
        this.dom = {};
        this.cacheDOM();
        this.init();
    }

    cacheDOM() {
        // Login
        this.dom.loginScreen = document.getElementById('login-screen');
        this.dom.adminInterface = document.getElementById('admin-interface');
        this.dom.loginBtn = document.getElementById('login-btn');
        this.dom.passwordInput = document.getElementById('password-input');
        this.dom.loginError = document.getElementById('login-error');

        // Cancel Edit
        this.dom.cancelEditBtn = document.getElementById('cancel-edit-btn');

        // Tabs
        this.dom.quizControlTab = document.getElementById('quiz-control-tab');
        this.dom.questionManagementTab = document.getElementById('question-management-tab');
        this.dom.settingsTab = document.getElementById('settings-tab');

        // Quiz controls
        this.dom.startQuizBtn = document.getElementById('start-quiz-btn');
        this.dom.revealAnswerBtn = document.getElementById('reveal-answer-btn');
        this.dom.nextQuestionBtn = document.getElementById('next-question-btn');
        this.dom.endQuizBtn = document.getElementById('end-quiz-btn');

        // Question form
        this.dom.questionType = document.getElementById('question-type');
        this.dom.questionContent = document.getElementById('question-content');
        this.dom.correctAnswer = document.getElementById('correct-answer');
        this.dom.correctAnswerGroup = this.dom.correctAnswer?.parentElement;
        this.dom.optionsGroup = document.getElementById('options-group');
        this.dom.addQuestionBtn = document.getElementById('add-question-btn');
        this.dom.addMcqOptionBtn = document.getElementById('add-mcq-option-btn');
        this.dom.mcqOptionsList = document.getElementById('mcq-options-list');
        this.dom.questionsList = document.getElementById('questions-list');
        this.dom.setupHeader = document.querySelector('.question-setup h3');

        // Status/display
        this.dom.status = document.getElementById('status');
        this.dom.participantCount = document.getElementById('participant-count');
        this.dom.quizStatus = document.getElementById('quiz-status');
        this.dom.currentQuestionStatus = document.getElementById('current-question-status');
        this.dom.answerCounter = document.getElementById('answer-counter');
        this.dom.questionText = document.getElementById('question-text');
        this.dom.adminQuestionProgress = document.getElementById('admin-question-progress');
        this.dom.adminTimeRemaining = document.getElementById('admin-time-remaining');

        // Answers/Leaderboard
        this.dom.answersDisplay = document.getElementById('answers-display');
        this.dom.answersTbody = document.getElementById('answers-tbody');
        this.dom.leaderboardTbody = document.getElementById('leaderboard-tbody');

        // Drawing
        this.dom.adminDrawCanvas = document.getElementById('admin-draw-canvas');
        this.dom.drawingArea = document.getElementById('drawing-area');
        this.dom.clearCanvasBtn = document.getElementById('clear-canvas');
        this.dom.finishDrawingBtn = document.getElementById('finish-drawing');

        // WoF Board
        this.dom.wofBoardArea = document.getElementById('wof-board-area');

        // Settings
        this.dom.questionTimer = document.getElementById('question-timer');
        this.dom.maxParticipants = document.getElementById('max-participants');
        this.dom.saveSettingsBtn = document.getElementById('save-settings-btn');
    }

    init() {
        this.setupLogin();
        this.setupTabs();
        this.updateStatus('Ready to login');
    }

    // ===== LOGIN =====
    setupLogin() {
        this.dom.loginBtn.addEventListener('click', () => this.attemptLogin());
        this.dom.passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.attemptLogin();
        });
    }

    attemptLogin() {
        this.isAuthenticated = true;
        this.dom.loginScreen.classList.add('hidden');
        this.dom.adminInterface.classList.remove('hidden');
        this.setupWebSocket();
        this.setupAdminControls();
        this.updateStatus('Logged in - Setting up quiz controls');
    }

    // ===== TABS =====
    setupTabs() {
        this.dom.quizControlTab.addEventListener('click', () => this.switchTab('quiz-control'));
        this.dom.questionManagementTab.addEventListener('click', () => {
            this.switchTab('question-management');
            this.loadQuestions();
        });
        this.dom.settingsTab.addEventListener('click', () => this.switchTab('settings'));
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        document.getElementById(`${tabName}-tab`).classList.add('active');
        document.getElementById(`${tabName}-content`).classList.add('active');
        this.currentTab = tabName;
    }

    // ===== WEBSOCKET =====
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/admin`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateStatus('Connected to quiz server');
            setTimeout(() => this.loadQuestions(), 100);
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

    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected');
        }
    }

    // ===== ADMIN CONTROLS SETUP =====
    setupAdminControls() {
        this.setupQuizButtons();
        this.setupQuestionForm();
        this.setupDrawingCanvas();
        this.setupSettings();
    }

    setupQuizButtons() {
        this.dom.startQuizBtn.addEventListener('click', () => {
            this.sendMessage({ type: 'start_quiz' });

            // Immediately clear leaderboard and answers UI for new quiz
            if (this.dom.leaderboardTbody) {
                this.dom.leaderboardTbody.innerHTML = '';
                const row = this.dom.leaderboardTbody.insertRow();
                row.className = 'no-scores';
                const cell = row.insertCell();
                cell.colSpan = 3;
                cell.textContent = 'No scores yet...';
            }
            if (this.dom.answersTbody) {
                this.dom.answersTbody.innerHTML = '';
                const row = this.dom.answersTbody.insertRow();
                row.className = 'no-answers';
                const cell = row.insertCell();
                cell.colSpan = 4;
                cell.textContent = 'Waiting for answers...';
            }
        });

        this.dom.revealAnswerBtn.addEventListener('click', () => {
            this.sendMessage({ type: 'reveal_answer' });
        });

        this.dom.nextQuestionBtn.addEventListener('click', () => {
            this.sendMessage({ type: 'next_question' });
        });

        this.dom.endQuizBtn.addEventListener('click', () => {
            this.sendMessage({ type: 'end_quiz' });
        });
    }

    setupQuestionForm() {
        this.dom.questionsList.addEventListener('click', (e) => {
            if (e.target.classList.contains('edit-btn')) {
                const idx = parseInt(e.target.dataset.index, 10);
                this.startEditQuestion(idx);
            }
            if (e.target.classList.contains('delete-btn')) {
                const idx = parseInt(e.target.dataset.index, 10);
                this.deleteQuestion(idx);
            }
        });

        this.dom.addQuestionBtn.addEventListener('click', () => this.addQuestion());

        this.dom.questionType.addEventListener('change', (e) => {
            this.toggleMCQOptions(e.target.value === 'multiple_choice');
        });

        this.dom.addMcqOptionBtn.onclick = () => this.appendMCQOptionRow();

        this.dom.cancelEditBtn.addEventListener('click', () => this.clearQuestionForm());
    }

    setupSettings() {
        this.dom.saveSettingsBtn.addEventListener('click', () => this.saveSettings());
    }

    // ===== QUESTION TYPE TOGGLING =====
toggleMCQOptions(showMCQ) {
    if (showMCQ) {
        this.dom.optionsGroup.style.display = 'block';
        this.dom.correctAnswerGroup.style.display = 'none';
        // Do NOT clear or re-render options here; let add or edit handlers invoke renderMCQOptions as needed.
    } else {
        this.dom.optionsGroup.style.display = 'none';
        this.dom.correctAnswerGroup.style.display = 'block';
        this.dom.correctAnswer.value = '';
        // When leaving MCQ mode, clear any MCQ option rows (optional, or just leave for UX)
    }
}

    // ===== MCQ OPTIONS =====
    renderMCQOptions(options, correctIdx) {
        this.dom.mcqOptionsList.innerHTML = '';
        const rows = (options && options.length > 0) ? options.length : 2;
        for (let i = 0; i < rows; i++) {
            const value = (options && options[i]) ? options[i] : '';
            this.appendMCQOptionRow(value, correctIdx === i);
        }
    }

    appendMCQOptionRow(value = '', checked = false) {
        const row = document.createElement('div');
        row.className = 'mcq-option-row';

        row.innerHTML = `
            <input type="radio" name="mcq-correct-radio" style="margin-right:4px;" ${checked ? 'checked' : ''} />
            <input type="text" class="mcq-option-input" placeholder="Option text" style="width:180px; margin-right:4px;" />
            <button type="button" class="btn btn-small btn-outline mcq-remove-option" title="Remove Option">&times;</button>
        `;

        row.querySelector('.mcq-option-input').value = value;

        row.querySelector('.mcq-remove-option').onclick = () => {
            if (this.dom.mcqOptionsList.childElementCount > 2) row.remove();
        };

        row.querySelector('input[type="radio"]').onclick = () => {
            document.querySelectorAll('#mcq-options-list input[type="radio"]').forEach(r => r.checked = false);
            row.querySelector('input[type="radio"]').checked = true;
        };

        this.dom.mcqOptionsList.appendChild(row);
    }

    getMCQOptionsAndCorrect() {
        const rows = document.querySelectorAll('#mcq-options-list .mcq-option-row');
        const options = [];
        let correctIndex = null;

        rows.forEach((row, idx) => {
            const txt = row.querySelector('.mcq-option-input').value.trim();
            options.push(txt);
            if (row.querySelector('input[type="radio"]').checked) correctIndex = idx;
        });

        return { options, correctIndex };
    }

    // ===== QUESTION MANAGEMENT =====
    validateQuestion(type, content, correctAnswer, options = null, correctIndex = null) {
        if (!content.trim()) {
            return 'Please enter a question';
        }

        if (type === 'multiple_choice') {
            if (options.some(o => !o.trim())) {
                return 'All options must be filled in';
            }
            if (correctIndex === null) {
                return 'Please select the correct answer';
            }
        } else if (type !== 'word_cloud') {
            if (!correctAnswer.trim()) {
                return 'Please enter the correct answer';
            }
        }

        // No correct answer needed for word_cloud
        return null;
    }

    addQuestion() {
        const type = this.dom.questionType.value;
        const content = this.dom.questionContent.value.trim();

        let question;
        let error;

        if (type === 'multiple_choice') {
            const { options, correctIndex } = this.getMCQOptionsAndCorrect();
            error = this.validateQuestion(type, content, '', options, correctIndex);

            if (error) {
                this.showMessage(error, 'error');
                return;
            }

            question = {
                type,
                content,
                options,
                correct_answer: options[correctIndex],
                correct_index: correctIndex,
                category: 'general'
            };
        } else if (type === 'word_cloud') {
            // Do not require or include correct_answer for word_cloud
            error = this.validateQuestion(type, content, '');

            if (error) {
                this.showMessage(error, 'error');
                return;
            }
            question = {
                type,
                content,
                correct_answer: '', // explicit empty; backend ignores
                category: 'general'
            };
        } else {
            const correctAnswer = this.dom.correctAnswer.value.trim();
            error = this.validateQuestion(type, content, correctAnswer);

            if (error) {
                this.showMessage(error, 'error');
                return;
            }

            question = {
                type,
                content,
                correct_answer: correctAnswer,
                category: 'general'
            };
        }

        const messageType = this.editingQuestionIndex !== undefined ? 'edit_question' : 'add_question';
        const message = { type: messageType, question };

        if (this.editingQuestionIndex !== undefined) {
            message.index = this.editingQuestionIndex;
        }

        this.sendMessage(message);
        this.clearQuestionForm();
        const msg = this.editingQuestionIndex !== undefined ? 'Question updated!' : 'Question added!';
        this.showMessage(msg, 'success');
    }

    clearQuestionForm() {
        this.editingQuestionIndex = undefined;
        this.dom.questionType.value = 'text';
        this.dom.questionContent.value = '';
        this.dom.correctAnswer.value = '';
        this.dom.addQuestionBtn.textContent = 'Add Question';
        this.dom.setupHeader.textContent = 'Add New Question';
        this.toggleMCQOptions(false);
        this.renderMCQOptions([], null);
        if (this.dom.cancelEditBtn) {
            this.dom.cancelEditBtn.style.display = 'none';
        }
    }

    startEditQuestion(index) {
        const question = this.questions[index];
        if (!question) return;

        this.editingQuestionIndex = index;

        // No normalization needed; trust database value of question.type
        this.dom.questionType.value = question.type;
        this.dom.questionContent.value = question.content;

        if (question.type === 'multiple_choice') {
            // Debug logging for MCQ parsing
            let opts = [];
            let optsRaw = question.options;
            console.log('[MCQ debug] startEditQuestion: raw question.options:', optsRaw);
            try {
                if (Array.isArray(optsRaw)) {
                    opts = optsRaw;
                    console.log('[MCQ debug] options is already an array:', opts);
                } else if (typeof optsRaw === 'string') {
                    let attempted = 0;
                    while (typeof optsRaw === 'string' && attempted < 3) {
                        console.log('[MCQ debug] Parsing options JSON (level', attempted, '):', optsRaw);
                        optsRaw = JSON.parse(optsRaw);
                        attempted++;
                    }
                    if (Array.isArray(optsRaw)) {
                        opts = optsRaw;
                        console.log('[MCQ debug] unwrapped array after JSON parse(s):', opts);
                    } else {
                        console.log('[MCQ debug] did not resolve to array after JSON parse(s):', optsRaw);
                    }
                } else {
                    console.log('[MCQ debug] options is unknown type:', typeof optsRaw, optsRaw);
                }
            } catch (e) {
                console.log('[MCQ debug] error parsing options:', e, 'optsRaw:', optsRaw);
                opts = [];
            }
            // Guarantee minimum 2 rows for user input
            if (!opts || !Array.isArray(opts) || opts.length === 0) {
                console.log('[MCQ debug] options fallback to blanks. Value was:', opts);
                opts = ['', ''];
            }

            const correctIdx = typeof question.correct_index !== 'undefined'
                ? question.correct_index
                : (Array.isArray(opts) ? opts.findIndex(o => o === (question.correct_answer || '')) : null);

            console.log('[MCQ debug] final options for renderMCQOptions:', opts, 'correctIdx:', correctIdx);

            this.toggleMCQOptions(true);
            this.renderMCQOptions(opts, correctIdx >= 0 ? correctIdx : null);
        } else {
            this.toggleMCQOptions(false);
            this.dom.correctAnswer.value = question.correct_answer;
        }

        this.dom.addQuestionBtn.textContent = 'Update Question';
        this.dom.setupHeader.textContent = 'Edit Question';

        if (this.dom.cancelEditBtn) {
            this.dom.cancelEditBtn.style.display = '';
        }
    }

    deleteQuestion(index) {
        if (confirm('Are you sure you want to delete this question?')) {
            this.sendMessage({ type: 'delete_question', index });
        }
    }

    updateQuestionsList(questions) {
        this.questions = questions;
        this.dom.questionsList.innerHTML = '';

        if (!questions || questions.length === 0) {
            this.dom.questionsList.textContent = 'No questions added yet...';
            return;
        }

        const categoryCounts = {};
        questions.forEach(q => {
            categoryCounts[q.category] = (categoryCounts[q.category] || 0) + 1;
        });

        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'questions-summary';
        summaryDiv.innerHTML = `
            <h4>Question Library Summary</h4>
            <div class="category-counts">
                ${Object.entries(categoryCounts).map(([cat, count]) =>
                    `<span class="category-badge">${this.escapeHtml(cat)}: ${count}</span>`
                ).join('')}
            </div>
            <div class="total-count">Total: ${questions.length} questions</div>
        `;
        this.dom.questionsList.appendChild(summaryDiv);

        const questionsHeader = document.createElement('h4');
        questionsHeader.textContent = 'Individual Questions';
        questionsHeader.style.marginTop = '20px';
        this.dom.questionsList.appendChild(questionsHeader);

        // Serial number table header
        const table = document.createElement('table');
        table.className = 'questions-table';
        table.style.width = '100%';
        table.innerHTML = `<thead>
            <tr>
                <th style="width:3ch;">#</th>
                <th>Type</th>
                <th>Category</th>
                <th>Content</th>
                <th>Answer</th>
                <th style="width:110px;">Actions</th>
            </tr>
        </thead><tbody></tbody>`;
        this.dom.questionsList.appendChild(table);
        const tbody = table.querySelector('tbody');

        // Drag & drop version of reorderable questions
        let dragSrcIdx = null;

        questions.forEach((question, index) => {
            const tr = document.createElement('tr');
            tr.setAttribute('draggable', 'true');
            tr.setAttribute('data-index', index);
            tr.classList.add('draggable-question-row');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <strong>${this.escapeHtml(question.type)}</strong>
                    <br/>
                    <small style="color:#aaa;">${this.escapeHtml(question.type.replaceAll('_', ' ').toUpperCase())}</small>
                </td>
                <td>${this.escapeHtml(question.category)}</td>
                <td>${this.escapeHtml(question.content)}</td>
                <td>${this.escapeHtml(question.correct_answer)}</td>
                <td>
                    <button class="btn btn-primary btn-small edit-btn" data-index="${index}">Edit</button>
                    <button class="btn btn-danger btn-small delete-btn" data-index="${index}">Delete</button>
                </td>
            `;

            // DnD handlers
            tr.addEventListener('dragstart', (ev) => {
                dragSrcIdx = index;
                tr.classList.add('dragging');
                ev.dataTransfer.effectAllowed = 'move';
            });
            tr.addEventListener('dragover', (ev) => {
                ev.preventDefault();
                tr.classList.add('drag-over');
            });
            tr.addEventListener('dragleave', () => {
                tr.classList.remove('drag-over');
            });
            tr.addEventListener('drop', (ev) => {
                ev.preventDefault();
                tr.classList.remove('drag-over');
                tr.classList.remove('dragging');
                const dragDestIdx = parseInt(tr.getAttribute('data-index'), 10);
                if (dragSrcIdx !== null && dragDestIdx !== null && dragSrcIdx !== dragDestIdx) {
                    this.moveQuestion(dragSrcIdx, dragDestIdx);
                }
                dragSrcIdx = null;
            });
            tr.addEventListener('dragend', () => {
                tr.classList.remove('drag-over');
                tr.classList.remove('dragging');
                dragSrcIdx = null;
            });

            tbody.appendChild(tr);
        });
    }

    loadQuestions() {
        this.sendMessage({ type: 'get_questions' });
    }

    // Move question from one index to another in local questions array and send update to backend
    moveQuestion(fromIndex, toIndex) {
        if (
            fromIndex < 0 || fromIndex >= this.questions.length ||
            toIndex < 0 || toIndex >= this.questions.length ||
            fromIndex === toIndex
        ) return;
        // Swap in questions array
        const temp = this.questions[fromIndex];
        this.questions[fromIndex] = this.questions[toIndex];
        this.questions[toIndex] = temp;
        // Optimistically update displayed list
        this.updateQuestionsList(this.questions);

        // Send new order to backend as a list of IDs (minimal payload)
        const newOrder = this.questions.map(q => q.id);
        this.sendMessage({
            type: 'reorder_questions',
            order: newOrder
        });
    }

    // ===== DRAWING =====
    setupDrawingCanvas() {
        const canvas = this.dom.adminDrawCanvas;
        const ctx = canvas.getContext('2d');

        this.drawing.canvas = canvas;
        this.drawing.ctx = ctx;

        canvas.width = 800;
        canvas.height = 600;

        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        canvas.addEventListener('mousedown', (e) => this.startDrawing(e, canvas));
        canvas.addEventListener('mousemove', (e) => this.draw(e, canvas));
        canvas.addEventListener('mouseup', () => this.stopDrawing());
        canvas.addEventListener('mouseout', () => this.stopDrawing());

        // Touch events
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            canvas.dispatchEvent(new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            }));
        });

        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            canvas.dispatchEvent(new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            }));
        });

        canvas.addEventListener('touchend', () => {
            canvas.dispatchEvent(new MouseEvent('mouseup'));
        });

        this.dom.clearCanvasBtn.addEventListener('click', () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });

        // Rename button label to "Hide Drawing"
        this.dom.finishDrawingBtn.textContent = 'Hide Drawing';
        this.dom.finishDrawingBtn.addEventListener('click', () => {
            // Formerly "push_drawing" -- now just hide, keep for backward compatibility if backend expects it
            this.sendMessage({ type: 'push_drawing' });
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            this.dom.drawingArea.classList.add('hidden');
        });
    }

    startDrawing(e, canvas) {
        this.drawing.isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        this.drawing.lastPos = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    draw(e, canvas) {
        if (!this.drawing.isDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentPos = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };

        const ctx = this.drawing.ctx;
        ctx.beginPath();
        ctx.moveTo(this.drawing.lastPos.x, this.drawing.lastPos.y);
        ctx.lineTo(currentPos.x, currentPos.y);
        ctx.stroke();

        this.sendMessage({
            type: 'drawing_stroke',
            stroke: {
                from: this.drawing.lastPos,
                to: currentPos,
                color: ctx.strokeStyle,
                width: ctx.lineWidth
            }
        });

        this.drawing.lastPos = currentPos;
    }

    stopDrawing() {
        this.drawing.isDrawing = false;
    }

    // ===== MESSAGE HANDLING =====
    handleMessage(data) {
        switch (data.type) {
            case 'question_add_error':
            case 'question_edit_error':
                this.showMessage(data.error || "Unknown error with question type.", 'error');
                break;
            case 'wof_update':
                this.handleWofUpdate(data);
                break;
            case 'wof_winner':
                this.handleWofWinner(data);
                break;
            case 'status_update':
                this.updateStatusDashboard(data);
                break;

            case 'quiz_started':
                this.setQuizUIState('started');
                if (data.progress) {
                    this.dom.adminQuestionProgress.textContent = 
                        `Question ${data.progress.current} of ${data.progress.total}`;
                }
                this.updateStatus('Quiz started');
                break;

            case 'question_pushed':
                this.handleQuestionPushed(data);
                break;

            case 'answer_revealed':
                this.showRevealedAnswer(data);
                this.setButtonState(this.dom.nextQuestionBtn, false);
                break;

            case 'word_cloud_revealed':
                this.showWordCloud(data.word_cloud);
                break;

            case 'reveal_confirmed':
                this.updateStatus('Answer revealed to all participants');
                this.setButtonState(this.dom.revealAnswerBtn, true);
                break;

            case 'reveal_error':
                this.showMessage('Error: ' + data.message, 'error');
                break;

            case 'timer_update':
                this.dom.adminTimeRemaining.textContent = data.time_left;
                break;

            case 'answer_received':
                this.updateAnswersList(data.answers);
                if (data.leaderboard && data.leaderboard.length > 0) {
                    this.updateLeaderboard(data.leaderboard);
                }
                break;

            case 'scores_updated':
                this.updateLeaderboard(data.scores);
                break;

            case 'quiz_ended':
                this.setQuizUIState('ended');
                this.updateStatus('Quiz ended');
                break;

            case 'questions_loaded':
                this.updateQuestionsList(data.questions);
                break;

            case 'question_added':
            case 'question_updated':
            case 'question_deleted':
                this.loadQuestions();
                break;

            case 'time_expired':
                this.setButtonState(this.dom.revealAnswerBtn, false);
                break;
        }
    }

    handleQuestionPushed(data) {
        // Remove old winner message (keep the static WoF board)
        const prevWinner = document.getElementById('wof-winner-msg');
        if (prevWinner) prevWinner.remove();

        const existingReveal = document.getElementById('admin-reveal');
        if (existingReveal) existingReveal.remove();

        // Display question text based on type
        if (data.question.type === 'wheel_of_fortune') {
            this.dom.questionText.innerHTML = `Guess the word in category: <span class="wof-category">${this.escapeHtml(data.question.content)}</span>`;
        } else {
            this.dom.questionText.textContent = data.question.content;
        }

        if (data.progress) {
            this.dom.adminQuestionProgress.textContent = 
                `Question ${data.progress.current} of ${data.progress.total}`;
            const isLastQuestion = data.progress.current >= data.progress.total;
            this.setButtonState(this.dom.nextQuestionBtn, isLastQuestion);
        }

        this.resetAnswerCounter();

        // Drawing area visibility and clearing logic
        const drawingArea = this.dom.drawingArea;
        const canvas = this.dom.adminDrawCanvas;
        const ctx = this.drawing?.ctx || (canvas ? canvas.getContext('2d') : null);
        if (data.question.type === 'pictionary') {
            drawingArea.classList.remove('hidden');
            if (ctx && canvas) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            }
        } else {
            drawingArea.classList.add('hidden');
        }

        // WoF board visibility
        const wofBoardArea = this.dom.wofBoardArea;
        if (data.question.type === 'wheel_of_fortune') {
            console.log('[DEBUG] Showing WoF board for question:', data.question);
            wofBoardArea.classList.remove('hidden');
            // Initialize with all underscores
            const boardDiv = wofBoardArea.querySelector('.wof-tiles');
            if (boardDiv) {
                const underscores = '_'.repeat(data.question.correct_answer?.length || 0);
                console.log('[DEBUG] Initializing board with underscores:', underscores);
                boardDiv.textContent = underscores;
            } else {
                console.error('[DEBUG] Could not find .wof-tiles element');
            }
        } else {
            wofBoardArea.classList.add('hidden');
        }

        this.setButtonState(this.dom.revealAnswerBtn, false);
    }

    handleWofUpdate(data) {
        // Update the board content (visibility handled by handleQuestionPushed)
        const boardDiv = document.querySelector('.wof-tiles');
        if (boardDiv) {
            boardDiv.textContent = data.board;
        }
        this.updateStatus(data.winner ? `Winner: ${data.winner}` : "Wheel of Fortune running...");
    }

    handleWofWinner(data) {
        const msg = document.getElementById('wof-winner-msg') || document.createElement('div');
        msg.id = 'wof-winner-msg';
        msg.className = 'wof-winner-msg';
        msg.innerHTML = `<h3>Winner: ${this.escapeHtml(data.winner)}</h3>
          <div>The answer was: <strong>${this.escapeHtml(data.answer)}</strong></div>`;
        this.dom.adminInterface.appendChild(msg);
        this.updateStatus(`Winner: ${data.winner}`);
    }

    // ===== UI STATE HELPERS =====
    setQuizUIState(state) {
        if (state === 'started') {
            this.setButtonState(this.dom.startQuizBtn, true);
            this.setButtonState(this.dom.revealAnswerBtn, false);
            this.setButtonState(this.dom.nextQuestionBtn, false);
            this.setButtonState(this.dom.endQuizBtn, false);
            this.dom.revealAnswerBtn.classList.remove('hidden');
        } else if (state === 'ended') {
            this.setButtonState(this.dom.startQuizBtn, false);
            this.setButtonState(this.dom.revealAnswerBtn, true);
            this.dom.revealAnswerBtn.classList.add('hidden');
            this.setButtonState(this.dom.nextQuestionBtn, false);
            this.setButtonState(this.dom.endQuizBtn, true);
        }
    }

    setButtonState(btn, disabled) {
        btn.disabled = disabled;
    }

    resetAnswerCounter() {
        const participantCount = parseInt(this.dom.participantCount.textContent) || 0;
        this.dom.answerCounter.textContent = 
            `0 answered (0 correct) out of ${participantCount} participants`;
    }

    // ===== ANSWERS & LEADERBOARD =====
    updateAnswersList(answers) {
        this.dom.answersTbody.innerHTML = '';
        const participantCount = parseInt(this.dom.participantCount.textContent) || 0;

        if (answers.length === 0) {
            const row = this.dom.answersTbody.insertRow();
            row.className = 'no-answers';
            const cell = row.insertCell();
            cell.colSpan = 4;
            cell.textContent = 'Waiting for answers...';
            this.resetAnswerCounter();
            return;
        }

        const totalAnswered = answers.length;
        // For word cloud: do not display "correct"/"✗" in admin table
        // Heuristic: if every answer.correct === false and every answer.score === 0, it's likely word cloud question (robust if backend tags type)
        const allUnknown = answers.every(a => a.correct === false && (!a.score || a.score === 0));

        const correctCount = answers.filter(a => a.correct).length;

        this.dom.answerCounter.textContent = 
            `${totalAnswered}/${participantCount} answered (${correctCount} correct)`;

        answers.sort((a, b) => (b.score || 0) - (a.score || 0));

        if (allUnknown) {
            // Word cloud: show only participant name and their submission
            answers.forEach((answer, index) => {
                this.addTableRow(this.dom.answersTbody, [
                    `#${index + 1}`,
                    answer.user,
                    answer.content
                ], [
                    'rank',
                    '',
                    'submission'
                ]);
            });
        } else {
            // Default: old logic, show ✓/✗ etc
            answers.forEach((answer, index) => {
                this.addTableRow(this.dom.answersTbody, [
                    `#${index + 1}`,
                    answer.user,
                    answer.score || 0,
                    answer.correct ? '✓' : '✗'
                ], [
                    'rank',
                    '',
                    'score',
                    answer.correct ? 'correct' : 'incorrect'
                ]);
            });
        }
    }

    updateLeaderboard(scores) {
        this.dom.leaderboardTbody.innerHTML = '';

        if (scores.length === 0) {
            const row = this.dom.leaderboardTbody.insertRow();
            row.className = 'no-answers';
            const cell = row.insertCell();
            cell.colSpan = 3;
            cell.textContent = 'No scores yet...';
            return;
        }

        const topScores = scores.slice(0, 10);

        topScores.forEach((score, index) => {
            this.addTableRow(this.dom.leaderboardTbody, [
                `#${index + 1}`,
                score.user_name,
                `${score.total_score} pts`
            ], [
                'rank',
                'name',
                'points'
            ]);
        });
    }

    addTableRow(tbody, values, classes = []) {
        const row = tbody.insertRow();
        values.forEach((value, idx) => {
            const cell = row.insertCell();
            cell.textContent = value;
            if (classes[idx]) cell.className = classes[idx];
        });
    }

    showRevealedAnswer(data) {
        this.setButtonState(this.dom.revealAnswerBtn, true);

        const revealDiv = document.createElement('div');
        revealDiv.id = 'admin-reveal';
        revealDiv.className = 'reveal-answer';
        revealDiv.innerHTML = `<h3>Revealed Answer: ${this.escapeHtml(data.correct_answer)}</h3>`;

        this.dom.answersDisplay.appendChild(revealDiv);
        this.updateStatus('Answer revealed');
    }

    showWordCloud(wordCloudData) {
        // Remove any existing reveal/word cloud displays
        const prev = document.getElementById('admin-reveal');
        if (prev) prev.remove();

        const wcDiv = document.createElement('div');
        wcDiv.id = 'admin-reveal';
        wcDiv.className = 'reveal-answer';
        wcDiv.innerHTML = `<h3>Word Cloud</h3>`;

        // Compute sizing (map frequency to font size: linear 1..max -> e.g. 18..56px)
        const maxSize = 56, minSize = 18;
        const max = Math.max(...wordCloudData.map(w => w.size), 1);

        wcDiv.style.display = 'flex';
        wcDiv.style.flexWrap = 'wrap';
        wcDiv.style.alignItems = 'center';
        wcDiv.style.gap = '12px';
        wcDiv.style.margin = '24px 0';

        wordCloudData.sort((a, b) => b.size - a.size);

        wordCloudData.forEach(word => {
            const span = document.createElement('span');
            const sizePx = minSize + Math.round((max > 1 ? (word.size - 1) / (max - 1) : 0) * (maxSize - minSize));
            span.textContent = word.text;
            span.style.fontSize = `${sizePx}px`;
            span.style.fontWeight = (sizePx > minSize + 8) ? 'bold' : 'normal';
            span.style.padding = '4px 8px';
            span.style.background = '#eff6ff';
            span.style.borderRadius = '8px';
            span.title = `Occurrences: ${word.size}`;
            wcDiv.appendChild(span);
        });

        this.dom.answersDisplay.appendChild(wcDiv);
        this.updateStatus('Word cloud generated and revealed');
    }

    // ===== STATUS DASHBOARD =====
    updateStatusDashboard(data) {
        const oldCount = parseInt(this.dom.participantCount.textContent) || 0;
        this.dom.participantCount.textContent = data.participant_count;

        if (oldCount !== data.participant_count) {
            this.updateAnswerCounter();
        }

        this.dom.quizStatus.textContent = data.quiz_active ? 'Active' : 'Waiting';

        const questionStatus = data.current_question ?
            (data.current_question.length > 20 ?
                data.current_question.substring(0, 20) + '...' :
                data.current_question) :
            'None';
        this.dom.currentQuestionStatus.textContent = questionStatus;

        if (data.hasOwnProperty('total_answered') && data.hasOwnProperty('correct_answers')) {
            const participantCount = data.participant_count;
            const totalAnswered = data.total_answered || 0;
            const correctCount = data.correct_answers || 0;
            this.dom.answerCounter.textContent = 
                `${totalAnswered} answered (${correctCount} correct) out of ${participantCount} participants`;
        }

        if (data.leaderboard && data.leaderboard.length > 0) {
            this.updateLeaderboard(data.leaderboard);
        }
    }

    updateAnswerCounter() {
        const rows = this.dom.answersTbody.querySelectorAll('tr:not(.no-answers)');
        const totalAnswered = rows.length;
        const correctCount = Array.from(rows).filter(row => row.querySelector('.correct')).length;
        const participantCount = parseInt(this.dom.participantCount.textContent) || 0;

        this.dom.answerCounter.textContent = 
            `${totalAnswered} answered (${correctCount} correct) out of ${participantCount} participants`;
    }

    // ===== SETTINGS =====
    saveSettings() {
        const questionTimer = parseInt(this.dom.questionTimer.value);
        const maxParticipants = parseInt(this.dom.maxParticipants.value);
        const wofTileDuration = parseFloat(document.getElementById('wof-tile-duration').value);

        if (questionTimer < 10 || questionTimer > 120) {
            this.showMessage('Question timer must be between 10 and 120 seconds', 'error');
            return;
        }

        if (maxParticipants < 1 || maxParticipants > 500) {
            this.showMessage('Max participants must be between 1 and 500', 'error');
            return;
        }

        if (isNaN(wofTileDuration) || wofTileDuration < 0.2 || wofTileDuration > 10) {
            this.showMessage('WoF tile duration must be between 0.2 and 10 seconds', 'error');
            return;
        }

        this.sendMessage({
            type: 'save_settings',
            settings: {
                question_timer: questionTimer,
                max_participants: maxParticipants,
                wof_tile_duration: wofTileDuration
            }
        });

        this.showMessage('Settings saved successfully!', 'success');
    }

    // ===== UTILITIES =====
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showMessage(message, type = 'info') {
        // Simple alert for now, can be enhanced with toast notifications later
        alert(message);
    }

    updateStatus(status) {
        this.dom.status.textContent = status;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new QuizAdmin();
});
