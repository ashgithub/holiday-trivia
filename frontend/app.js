// All-Hands Quiz Game - Participant Client
class QuizParticipant {
    constructor() {
        this.ws = null;
        this.currentQuestion = null;
        this.timer = null;
        this.timeLeft = 30;
        this.recognition = null;
        this.isListening = false;
        this.isProcessing = false;
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

        // Update waiting message with personalized welcome
        document.getElementById('waiting-message').innerHTML = `
            <h2>Welcome ${this.participantName}!</h2>
            <p>Waiting for the quiz to start...</p>
            <div class="snowflake">❄️</div>
        `;

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
        const rootPath = window.ROOT_PATH.replace(/\/$/, ''); // Remove trailing slash
        const wsUrl = `${protocol}//${window.location.host}${rootPath}/ws/participant`;

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
            this.toggleVoiceRecognition('text-answer');
        });


    }

    setupVoiceRecognition() {
        console.log('[VOICE DEBUG] Checking for speech recognition API...');
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            console.log('[VOICE DEBUG] Speech recognition API found');
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.recognition.onstart = () => {
                console.log('[VOICE DEBUG] Speech recognition started');
                this.isListening = true;
                this.isProcessing = false;
                this.updateVoiceButton(this.currentVoiceButton);
            };

            this.recognition.onresult = (event) => {
                console.log('[VOICE DEBUG] Speech recognition result received, processing...');

                let finalTranscript = '';
                let interimTranscript = '';

                // Process all results - some may be interim, some final
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    const transcript = result[0].transcript;

                    if (result.isFinal) {
                        finalTranscript += transcript;
                        console.log('[VOICE DEBUG] Final result:', transcript);
                    } else {
                        interimTranscript += transcript;
                        console.log('[VOICE DEBUG] Interim result:', transcript);
                    }
                }

                const targetInput = document.getElementById(this.currentVoiceInput);
                if (targetInput) {
                    // Show interim results with special styling, final results normally
                    if (interimTranscript && !finalTranscript) {
                        // Still getting interim results
                        targetInput.value = interimTranscript;
                        targetInput.classList.add('interim-speech');
                        this.isListening = true; // Keep listening state for interim
                        this.isProcessing = false;
                    } else if (finalTranscript) {
                        // Final result received
                        targetInput.value = finalTranscript;
                        targetInput.classList.remove('interim-speech');
                        this.isListening = false;
                        this.isProcessing = true;
                        this.updateVoiceButton(this.currentVoiceButton);

                        // Small delay to show processing state before returning to idle
                        setTimeout(() => {
                            this.isProcessing = false;
                            this.updateVoiceButton(this.currentVoiceButton);
                        }, 500);
                    }
                } else {
                    console.error('[VOICE DEBUG] Target input field not found:', this.currentVoiceInput);
                }
            };

            this.recognition.onend = () => {
                console.log('[VOICE DEBUG] Speech recognition ended');
                this.isListening = false;
                if (!this.isProcessing) {
                    this.updateVoiceButton(this.currentVoiceButton);
                }
            };

            this.recognition.onerror = (error) => {
                console.error('[VOICE DEBUG] Speech recognition error:', error);
                this.isListening = false;
                this.isProcessing = false;
                this.updateVoiceButton(this.currentVoiceButton);
                this.showVoiceError(error);
            };

            console.log('[VOICE DEBUG] Speech recognition initialized successfully');
        } else {
            console.warn('[VOICE DEBUG] Speech recognition API not available, hiding voice button');
            document.getElementById('voice-btn').style.display = 'none';
        }
    }

    toggleVoiceRecognition(targetInputId) {
        console.log('[VOICE DEBUG] Voice button clicked for', targetInputId, 'recognition available:', !!this.recognition, 'isListening:', this.isListening);
        if (!this.recognition) {
            console.error('[VOICE DEBUG] Speech recognition not available');
            return;
        }

        // Store which input field to update and which button to style
        this.currentVoiceInput = targetInputId;
        this.currentVoiceButton = 'voice-btn';

        if (this.isListening) {
            console.log('[VOICE DEBUG] Stopping speech recognition');
            this.recognition.stop();
        } else {
            console.log('[VOICE DEBUG] Starting speech recognition');
            try {
                this.recognition.start();
                this.isListening = true;
                this.updateVoiceButton(this.currentVoiceButton);
            } catch (error) {
                console.error('[VOICE DEBUG] Failed to start speech recognition:', error);
                this.showVoiceError(error);
            }
        }
    }

    updateVoiceButton(targetButtonId) {
        const btn = document.getElementById(targetButtonId || 'voice-btn');
        if (btn) {
            // Remove all state classes first
            btn.classList.remove('listening', 'processing');

            if (this.isListening) {
                btn.textContent = '🎤 Listening...';
                btn.classList.add('listening');
            } else if (this.isProcessing) {
                btn.textContent = '🎤 Processing...';
                btn.classList.add('processing');
            } else {
                btn.textContent = '🎤 Voice';
                // No additional classes for idle state
            }
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'quiz_started':
                soundManager.quizStarted();
                this.handleQuizStarted(data.progress);
                break;

            case 'question':
                this.displayQuestion(data.question, data.progress);
                break;

            case 'wof_update':
                this.handleWofUpdate(data);
                break;

            case 'wof_winner':
                this.handleWofWinner(data);
                break;

            case 'wof_countdown_started':
                // Show timer and start WoF countdown
                const timerElement = document.getElementById('timer');
                if (timerElement) {
                    timerElement.classList.remove('hidden');
                }
                this.timeLeft = data.timer_duration;
                this.updateTimerDisplay();
                // Start countdown
                if (this.timer) clearInterval(this.timer);
                this.timer = setInterval(() => {
                    this.timeLeft--;
                    this.updateTimerDisplay();
                    if (this.timeLeft <= 0) {
                        clearInterval(this.timer);
                        this.timeExpired();
                    }
                }, 1000);
                break;

            case 'personal_feedback':
                this.showPersonalFeedback(data);
                break;

            case 'answer_revealed':
                this.showRevealedAnswer(data);
                break;





            case 'timer_update':
                // Show timer when countdown starts for regular questions
                const participantTimer = document.getElementById('timer');
                if (participantTimer) {
                    participantTimer.classList.remove('hidden');
                }
                // Conditionally add "s" only for numeric values
                if (this.timeLeft > 0 && !this.hasSubmitted) {
                    const timeText = (typeof data.time_left === 'number') ?
                        `${data.time_left}s` :
                        data.time_left;
                    document.getElementById('time-remaining').textContent = timeText;
                }
                break;

            case 'quiz_ended':
                this.showWaitingMessage();
                break;
        }
    }

    handleWofUpdate(data) {
        soundManager.wofReveal();
        // For participants, do NOT display the tiles or input.
        // Only update the status with winner or "Wheel of Fortune running..."
        this.updateStatus(data.winner ? `Winner: ${data.winner}` : "Wheel of Fortune running...");
    }

    handleWofWinner(data) {
        // Show winner prominently
        const msg = document.getElementById('wof-winner-msg') || document.createElement('div');
        msg.id = 'wof-winner-msg';
        msg.className = 'wof-winner-msg';
        msg.innerHTML = `<h3>Winner: ${this.escapeHtml(data.winner)}</h3>
          <div>The answer was: <strong>${this.escapeHtml(data.answer)}</strong></div>`;
        document.getElementById('question-container').appendChild(msg);
        // Lock input if present
        let inp = document.getElementById('wof-input');
        let btn = document.getElementById('wof-submit-btn');
        if (inp) inp.disabled = true;
        if (btn) btn.disabled = true;
        this.updateStatus(`Winner: ${data.winner}`);
    }

    submitWofGuess() {
        const inp = document.getElementById('wof-input');
        if (!inp || !inp.value.trim()) return;
        if (!this.currentQuestion) return;
        this.ws.send(JSON.stringify({
            type: "answer",
            question_id: this.currentQuestion.id,
            answer: inp.value
        }));
        inp.value = "";
    }

    showQuestionContainer() {
        document.getElementById('waiting-message').classList.add('hidden');
        document.getElementById('question-container').classList.remove('hidden');
    }

    handleQuizStarted(progress) {
        // Show quiz started waiting message with progress info
        const waitingMessage = document.getElementById('waiting-message');
        waitingMessage.innerHTML = `
            <h2>Quiz Started! 🎉</h2>
            <p>Waiting for the first question...</p>
            <div class="question-progress">Question ${progress.current} of ${progress.total}</div>
            <div class="snowflake">❄️</div>
        `;
        this.updateStatus('Quiz started - Waiting for first question');
    }



    showWaitingMessage() {
        document.getElementById('question-container').classList.add('hidden');
        document.getElementById('waiting-message').classList.remove('hidden');
        document.getElementById('waiting-message').innerHTML = `
            <h2>Quiz Finished!</h2>
            <p>Thanks for playing! The quiz has ended.</p>
            <div class="snowflake">🎉</div>
        `;
        this.updateStatus('Quiz ended - Thanks for playing!');
    }

    displayQuestion(question, progress) {
        soundManager.questionPosted();
        this.currentQuestion = question;
        this.hasSubmitted = false; // Reset submission flag for new question
        this.allowMultiple = question.allow_multiple || true;

        // Show question container and hide waiting message
        this.showQuestionContainer();

        // Remove any old WoF board, input, or winner UI
        ['wof-board', 'wof-input', 'wof-submit-btn', 'wof-winner-msg'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.remove();
        });

        // Restore timer markup for new question - hide timer initially
        const timer = document.getElementById('timer');
        timer.innerHTML = '<span>Time remaining: <span id="time-remaining"></span></span><span id="feedback-slot"></span>';
        timer.classList.add('hidden');

        // Update progress display
        if (progress) {
            document.getElementById('question-progress').textContent = `Question ${progress.current} of ${progress.total}`;
        }

        // Display question text based on type
        if (question.type === 'wheel_of_fortune') {
            document.getElementById('question-content').innerHTML =
                `<span class="wof-category">${this.escapeHtml(question.content)}</span>`;
        } else if (question.type === 'pictionary') {
            document.getElementById('question-content').textContent = "Look at the screen and guess what is being drawn!";
        } else {
            document.getElementById('question-content').textContent = question.content;
        }

        // Re-enable input fields for new question
        const textAnswer = document.getElementById('text-answer');
        const submitBtn = document.getElementById('submit-btn');
        textAnswer.disabled = false;
        textAnswer.value = ''; // Clear any previous answer
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit';

        // Clear feedback and revealed answers
        this.clearFeedback();
        this.clearRevealedAnswer();

        // Handle different question types
        if (question.type === 'multiple_choice') {
            this.showMultipleChoice(question.options);
        } else {
            this.hideMultipleChoice();
        }

        // Only start timer for non-WoF questions
        // WoF timer starts when admin clicks "Start Countdown"
        if (question.type !== 'wheel_of_fortune') {
            this.resetTimer();
        }
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
            // Remove auto-highlight and rely only on submit+disable feedback
            container.appendChild(btn);
        });
    }

    hideMultipleChoice() {
        document.getElementById('multiple-choice-options').classList.add('hidden');
    }

    selectChoice(index, text) {
        console.log('[MCQ DEBUG] selectChoice called - index:', index, 'text:', text, 'hasSubmitted:', this.hasSubmitted);

        // Prevent multiple submissions/disables after submission
        if (this.hasSubmitted) {
            console.log('[MCQ DEBUG] Preventing multiple submission - already submitted');
            return;
        }

        console.log('[MCQ DEBUG] Proceeding with MCQ selection');

        // Submit answer
        this.submitAnswer(text);

        // Disable all MCQ buttons immediately; no visual "selected" class
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = true;
            console.log('[MCQ DEBUG] Disabled MCQ button');
        });
    }

    // Simple HTML escape (same as admin.js)
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showPersonalFeedback(data) {
        const slot = document.getElementById('feedback-slot');
        if (!slot) return;

        // For word cloud: explicit status handling via scoring_status field
        if (data.scoring_status === 'pending') {
            slot.innerHTML = `<span class="feedback submitted">Answer submitted. Waiting for word cloud scoring...</span>`;
            document.getElementById('text-answer').disabled = true;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = 'Submitted';
            this.hasSubmitted = true;
        } else if (data.scoring_status === 'complete') {
            // Scored after clustering
            slot.innerHTML = `<span class="feedback wordcloud-result">Word cloud score: <strong>${data.score}</strong> (${data.cluster_size} in group: ${this.escapeHtml(data.cluster_rep || '')})</span>`;
            document.getElementById('text-answer').disabled = true;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = 'Scored';
            this.hasSubmitted = true;
            soundManager.answerCorrect(); // Treat as correct for scoring
        } else if (data.correct) {
            const currentScore = data.score || 0;
            const totalScore = data.total_score || 0;
            slot.innerHTML = `<span class="feedback correct">Correct! 🎉 (+${currentScore} pts, Total: ${totalScore} pts)</span>`;
            // Disable input for correct
            document.getElementById('text-answer').disabled = true;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = 'Correct!';
            this.hasSubmitted = true; // Keep as submitted
            soundManager.answerCorrect();
        } else if (data.allow_multiple && this.timeLeft > 0) {
            const retryCount = data.retry_count || 1;
            const totalScore = data.total_score || 0;
            slot.innerHTML = `<span class="feedback incorrect">Incorrect - try again! (Retry ${retryCount}, Total: ${totalScore} pts)</span>`;
            // Re-enable input for retry
            document.getElementById('text-answer').disabled = false;
            document.getElementById('submit-btn').disabled = false;
            document.getElementById('submit-btn').textContent = 'Submit';
            this.hasSubmitted = false;
            soundManager.answerWrong();
        } else {
            const totalScore = data.total_score || 0;
            slot.innerHTML = `<span class="feedback incorrect">Incorrect (Total: ${totalScore} pts)</span>`;
            // Keep disabled if no retry or time expired
            document.getElementById('text-answer').disabled = true;
            document.getElementById('submit-btn').disabled = true;
            soundManager.answerWrong();
        }
    }

    showRevealedAnswer(data) {
        // Disable input
        document.getElementById('text-answer').disabled = true;
        document.getElementById('submit-btn').disabled = true;

        // Show reveal
        const revealDiv = document.createElement('div');
        revealDiv.id = 'reveal';
        revealDiv.className = 'reveal-answer';
        revealDiv.innerHTML = `<h3>The answer is: ${data.correct_answer}</h3>`;
        if (data.options) {
            const optionsList = document.createElement('ul');
            data.options.forEach(opt => {
                const li = document.createElement('li');
                li.textContent = opt;
                if (opt.toLowerCase() === data.correct_answer.toLowerCase()) {
                    li.className = 'correct-option';
                }
                optionsList.appendChild(li);
            });
            revealDiv.appendChild(optionsList);
        }

        document.getElementById('question-container').appendChild(revealDiv);

        this.updateStatus('Answer revealed - waiting for next question');
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
        soundManager.answerSubmitted();
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
        const slot = document.getElementById('feedback-slot');
        if (slot) {
            slot.innerHTML = '<span class="feedback submitted">Submitted</span>';
        }

        // For single-attempt questions, keep disabled
        if (!this.allowMultiple) {
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
        soundManager.timerExpired();
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

        // Show time expired in feedback slot
        const slot = document.getElementById('feedback-slot');
        if (slot) {
            slot.innerHTML = '<span class="feedback expired">Time Expired</span>';
        }
    }

    updateTimerDisplay() {
        document.getElementById('time-remaining').textContent = this.timeLeft;
    }

    updateTimer(timeLeft) {
        this.timeLeft = timeLeft;
        this.updateTimerDisplay();
        if (this.timeLeft <= 10 && this.timeLeft > 0) {
            soundManager.timerCountdown();
        }
    }



    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }

    clearFeedback() {
        const slot = document.getElementById('feedback-slot');
        if (slot) {
            slot.innerHTML = '';
        }
    }

    clearRevealedAnswer() {
        const revealDiv = document.getElementById('reveal');
        if (revealDiv) {
            revealDiv.remove();
        }
    }

    showVoiceError(error) {
        console.error('[VOICE DEBUG] Showing voice error to user:', error);

        let message = 'Voice recognition failed. ';
        switch (error.error) {
            case 'not-allowed':
                message += 'Microphone access denied. Please allow microphone permissions and try again.';
                break;
            case 'no-speech':
                message += 'No speech detected. Please speak clearly into your microphone.';
                break;
            case 'audio-capture':
                message += 'Microphone not found or not accessible.';
                break;
            case 'network':
                message += 'Network error occurred. Check your connection.';
                break;
            case 'service-not-allowed':
                message += 'Speech recognition service not allowed. This may require HTTPS.';
                break;
            default:
                message += `Error: ${error.error || 'Unknown error'}. Please try typing your answer instead.`;
        }

        // Show error in status or as an alert
        this.updateStatus(`Voice Error: ${message}`);

        // Also show as alert for immediate attention
        alert(message);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new QuizParticipant();
});
