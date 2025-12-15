class SoundManager {
  constructor() {
    this.audioContext = null;
    this.init();
  }

  init() {
    // Initialize Web Audio API context on user interaction to avoid autoplay policy
    const initContext = () => {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
    };
    // Trigger on first user interaction
    document.addEventListener('click', initContext, { once: true });
    document.addEventListener('keydown', initContext, { once: true });
  }

  playTone(frequency, duration, type = 'sine', volume = 0.3) {
    if (!this.audioContext) return;
    const oscillator = this.audioContext.createOscillator();
    const gainNode = this.audioContext.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(this.audioContext.destination);
    oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
    oscillator.type = type;
    gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
    oscillator.start(this.audioContext.currentTime);
    oscillator.stop(this.audioContext.currentTime + duration);
  }

  // 1. Quiz Started: Festive jingle with bells (multiple tones)
  quizStarted() {
    // Simple bell sequence
    this.playTone(800, 0.5, 'sine', 0.4);
    setTimeout(() => this.playTone(1000, 0.5, 'sine', 0.4), 200);
    setTimeout(() => this.playTone(1200, 0.8, 'sine', 0.4), 400);
  }

  // 2. User Joined: Single merry bell ding
  userJoined() {
    this.playTone(1200, 0.3, 'sine', 0.5);
  }

  // 3. User Left: Soft fading chime
  userLeft() {
    this.playTone(600, 0.8, 'sine', 0.3); // Descending feel
  }

  // 4. Question Posted: Upbeat trumpet fanfare (sawtooth wave)
  questionPosted() {
    this.playTone(523, 0.2, 'sawtooth', 0.4); // C note
    setTimeout(() => this.playTone(659, 0.2, 'sawtooth', 0.4), 100); // E note
    setTimeout(() => this.playTone(784, 0.3, 'sawtooth', 0.4), 200); // G note
  }

  // 5. Answer Submitted: Light twinkling sound
  answerSubmitted() {
    this.playTone(1000, 0.1, 'sine', 0.3);
    setTimeout(() => this.playTone(1200, 0.1, 'sine', 0.3), 50);
    setTimeout(() => this.playTone(1400, 0.1, 'sine', 0.3), 100);
  }

  // 6. Answer Correct: Joyful chime with 'applause' (rapid chimes)
  answerCorrect() {
    this.playTone(800, 0.3, 'sine', 0.5);
    setTimeout(() => this.playTone(1000, 0.3, 'sine', 0.5), 100);
    // 'Applause' simulation with rapid notes
    for (let i = 0; i < 5; i++) {
      setTimeout(() => this.playTone(1200 + Math.random() * 200, 0.05, 'sine', 0.2), 300 + i * 50);
    }
  }

  // 7. Answer Wrong: Gentle buzzer (low frequency)
  answerWrong() {
    this.playTone(200, 0.5, 'sawtooth', 0.2);
    this.playTone(180, 0.5, 'sawtooth', 0.2); // Slight detune for buzz
  }

  // 8. Timer Countdown: Soft ticking (square wave)
  timerCountdown() {
    this.playTone(800, 0.05, 'square', 0.1); // Tick sound
  }

  // 9. Timer Expired: Final bell
  timerExpired() {
    this.playTone(400, 1.0, 'sine', 0.4); // Low bell
  }

  // 10. Wheel of Fortune Reveal: Whoosh with ding (noise + tone)
  wofReveal() {
    // Simple whoosh simulation (low freq sweep)
    const oscillator = this.audioContext.createOscillator();
    const gainNode = this.audioContext.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(this.audioContext.destination);
    oscillator.frequency.setValueAtTime(100, this.audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(50, this.audioContext.currentTime + 0.3);
    oscillator.type = 'sawtooth';
    gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3);
    oscillator.start(this.audioContext.currentTime);
    oscillator.stop(this.audioContext.currentTime + 0.3);
    // Ding
    setTimeout(() => this.playTone(1200, 0.2, 'sine', 0.5), 300);
  }

  // 11. Drawing Update: Subtle scribble (noise burst)
  drawingUpdate() {
    // Simple noise for scribble
    const bufferSize = this.audioContext.sampleRate * 0.05;
    const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
    const output = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }
    const noise = this.audioContext.createBufferSource();
    noise.buffer = buffer;
    const gainNode = this.audioContext.createGain();
    noise.connect(gainNode);
    gainNode.connect(this.audioContext.destination);
    gainNode.gain.setValueAtTime(0.05, this.audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.05);
    noise.start(this.audioContext.currentTime);
  }
}

// Global instance
const soundManager = new SoundManager();

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SoundManager, soundManager };
}
