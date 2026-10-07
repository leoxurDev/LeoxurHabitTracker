/**
 * Apple Design Standard — Habit Application Logic
 * Audio Chime, Precision Stopwatch, Assistant, 24h Timeline & Reminders
 */

// CSRF Token Helper
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// --- Apple Synthesized Audio Chimes (Web Audio API) ---
class iOSAudio {
  static playChime(type = 'success') {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();

      if (type === 'success') {
        // Delicate harmonic double ping
        const now = ctx.currentTime;
        [587.33, 880].forEach((freq, idx) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, now + idx * 0.07);
          gain.gain.setValueAtTime(0.12, now + idx * 0.07);
          gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.07 + 0.35);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now + idx * 0.07);
          osc.stop(now + idx * 0.07 + 0.38);
        });
      } else if (type === 'reminder') {
        // Subtle tri-tone reminder alert
        const now = ctx.currentTime;
        [523.25, 659.25, 783.99].forEach((freq, idx) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, now + idx * 0.09);
          gain.gain.setValueAtTime(0.15, now + idx * 0.09);
          gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.09 + 0.45);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now + idx * 0.09);
          osc.stop(now + idx * 0.09 + 0.5);
        });
      }
    } catch (e) {
      // Quiet fail if browser restricts audio before user interaction
    }
  }
}

// --- Toast Notification ---
function showiOSToast(message, icon = '✓') {
  let toast = document.getElementById('iosToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'iosToast';
    toast.className = 'ios-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2600);
}

// --- Precision Stopwatch / Habit Timer with LocalStorage Persistence ---
class HabitTimer {
  constructor() {
    this.seconds = 0;
    this.accumulated = 0;
    this.startTime = null;
    this.timerId = null;
    this.isRunning = false;

    this.display = document.getElementById('timerDigits');
    this.btn = document.getElementById('timerToggleBtn');
    this.resetBtn = document.getElementById('timerResetBtn');
    this.logBtn = document.getElementById('timerLogBtn');
    this.indicator = document.getElementById('timerIndicator');

    if (this.btn) {
      this.btn.addEventListener('click', () => this.toggle());
    }
    if (this.resetBtn) {
      this.resetBtn.addEventListener('click', () => this.reset());
    }
    if (this.logBtn) {
      this.logBtn.addEventListener('click', () => this.logSession());
    }

    this.restoreState();
  }

  saveState() {
    try {
      localStorage.setItem('habit_stopwatch_state', JSON.stringify({
        isRunning: this.isRunning,
        startTime: this.startTime,
        accumulated: this.accumulated
      }));
    } catch (e) {
      console.warn('Could not save stopwatch state', e);
    }
  }

  restoreState() {
    try {
      const saved = localStorage.getItem('habit_stopwatch_state');
      if (saved) {
        const state = JSON.parse(saved);
        this.accumulated = state.accumulated || 0;
        
        if (state.isRunning && state.startTime) {
          this.startTime = state.startTime;
          this.isRunning = true;
          const elapsedSinceStart = Math.floor((Date.now() - this.startTime) / 1000);
          this.seconds = Math.max(0, this.accumulated + elapsedSinceStart);
          this.render();
          
          if (this.btn) this.btn.innerText = 'Pause';
          if (this.indicator) {
            this.indicator.style.background = 'var(--apple-green)';
            this.indicator.style.boxShadow = '0 0 10px var(--apple-green)';
          }

          this.timerId = setInterval(() => {
            const currentElapsed = Math.floor((Date.now() - this.startTime) / 1000);
            this.seconds = Math.max(0, this.accumulated + currentElapsed);
            this.render();
          }, 1000);
        } else if (this.accumulated > 0) {
          this.seconds = this.accumulated;
          this.render();
          if (this.btn) this.btn.innerText = 'Resume';
          if (this.indicator) {
            this.indicator.style.background = 'var(--apple-orange)';
            this.indicator.style.boxShadow = 'none';
          }
        }
      }
    } catch (e) {
      console.warn('Could not restore stopwatch state', e);
    }
  }

  toggle() {
    if (this.isRunning) {
      this.stop();
    } else {
      this.start();
    }
  }

  start() {
    this.isRunning = true;
    this.startTime = Date.now();
    if (this.btn) this.btn.innerText = 'Pause';
    if (this.indicator) {
      this.indicator.style.background = 'var(--apple-green)';
      this.indicator.style.boxShadow = '0 0 10px var(--apple-green)';
    }

    this.saveState();

    if (this.timerId) clearInterval(this.timerId);
    this.timerId = setInterval(() => {
      const currentElapsed = Math.floor((Date.now() - this.startTime) / 1000);
      this.seconds = Math.max(0, this.accumulated + currentElapsed);
      this.render();
    }, 1000);
  }

  stop() {
    if (this.isRunning && this.startTime) {
      const elapsedSinceStart = Math.floor((Date.now() - this.startTime) / 1000);
      this.accumulated += Math.max(0, elapsedSinceStart);
    }
    this.seconds = this.accumulated;
    this.isRunning = false;
    this.startTime = null;

    if (this.btn) this.btn.innerText = 'Resume';
    if (this.indicator) {
      this.indicator.style.background = 'var(--apple-orange)';
      this.indicator.style.boxShadow = 'none';
    }
    clearInterval(this.timerId);
    this.saveState();
  }

  reset() {
    this.isRunning = false;
    this.seconds = 0;
    this.accumulated = 0;
    this.startTime = null;
    clearInterval(this.timerId);

    try {
      localStorage.removeItem('habit_stopwatch_state');
    } catch (e) {}

    if (this.btn) this.btn.innerText = 'Start';
    if (this.indicator) {
      this.indicator.style.background = 'var(--apple-green)';
      this.indicator.style.boxShadow = 'none';
    }
    this.render();
    showiOSToast('Stopwatch reset', '↺');
  }

  render() {
    if (!this.display) return;
    const h = Math.floor(this.seconds / 3600);
    const m = Math.floor((this.seconds % 3600) / 60);
    const s = this.seconds % 60;
    this.display.innerText = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  logSession() {
    if (this.seconds <= 0) {
      showiOSToast('Start the timer first to record elapsed time', '!');
      return;
    }
    const currentHour = new Date().getHours();
    openLogModal(currentHour, {
      title: 'Timed Focus Session',
      duration_val: this.seconds,
      unit_type: 'seconds',
      notes: `Recorded session: ${this.display.innerText}`
    });
    this.stop();
  }
}

// --- Activity Modal Logic ---
let activeHour = 0;
let selectedUnit = 'hours';
let selectedCategory = null;
let selectedEnergy = 4;

function openLogModal(hour, initialData = {}) {
  activeHour = hour;
  const modal = document.getElementById('activityModal');
  const modalHourTitle = document.getElementById('modalHourTitle');
  const modalHourInput = document.getElementById('modalHourInput');
  const titleInput = document.getElementById('modalTitleInput');
  const durationInput = document.getElementById('modalDurationInput');
  const notesInput = document.getElementById('modalNotesInput');
  const deleteBtn = document.getElementById('modalDeleteBtn');

  const period = hour < 12 ? 'AM' : 'PM';
  const displayH = hour % 12 === 0 ? 12 : hour % 12;
  const formattedHour = `${String(displayH).padStart(2, '0')}:00 ${period}`;

  if (modalHourTitle) modalHourTitle.innerText = `Hour ${formattedHour}`;
  if (modalHourInput) modalHourInput.value = hour;

  titleInput.value = initialData.title || '';
  notesInput.value = initialData.notes || '';
  durationInput.value = initialData.duration_val || 1;

  setModalUnit(initialData.unit_type || 'hours');
  setModalEnergy(initialData.energy || 4);

  selectedCategory = initialData.category_id || null;
  document.querySelectorAll('.category-tile').forEach(tile => {
    if (tile.dataset.catId == selectedCategory) {
      tile.classList.add('active');
    } else {
      tile.classList.remove('active');
    }
  });

  if (deleteBtn) {
    deleteBtn.style.display = initialData.title ? 'inline-flex' : 'none';
  }

  modal.classList.add('open');
}

function closeLogModal() {
  const modal = document.getElementById('activityModal');
  if (modal) modal.classList.remove('open');
}

function setModalUnit(unit) {
  selectedUnit = unit;
  document.querySelectorAll('.segmented-option').forEach(opt => {
    if (opt.dataset.unit === unit) {
      opt.classList.add('active');
    } else {
      opt.classList.remove('active');
    }
  });
  const durLabel = document.getElementById('modalDurationLabel');
  if (durLabel) {
    durLabel.innerText = `Duration (${unit.toUpperCase()})`;
  }
}

function setModalEnergy(level) {
  selectedEnergy = level;
  document.querySelectorAll('.energy-dot').forEach(dot => {
    if (parseInt(dot.dataset.level) === level) {
      dot.classList.add('active');
    } else {
      dot.classList.remove('active');
    }
  });
}

// --- Submit Activity Log ---
async function saveActivityLog() {
  const title = document.getElementById('modalTitleInput').value.trim();
  const durationVal = parseFloat(document.getElementById('modalDurationInput').value) || 1;
  const notes = document.getElementById('modalNotesInput').value.trim();
  const dateStr = document.getElementById('currentDateStr') ? document.getElementById('currentDateStr').value : '';

  const payload = {
    date: dateStr,
    hour: activeHour,
    title: title,
    category_id: selectedCategory,
    unit_type: selectedUnit,
    duration_value: durationVal,
    notes: notes,
    energy_level: selectedEnergy
  };

  try {
    const res = await fetch('/api/log-hour/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      iOSAudio.playChime('success');
      showiOSToast('Saved', '✓');
      closeLogModal();
      setTimeout(() => { window.location.reload(); }, 250);
    }
  } catch (err) {
    console.error('Error logging hour:', err);
    showiOSToast('Error saving log', '✕');
  }
}

// --- Delete Activity Log ---
async function deleteActivityLog() {
  const dateStr = document.getElementById('currentDateStr') ? document.getElementById('currentDateStr').value : '';
  if (!confirm('Clear activity for this hour?')) return;

  try {
    const res = await fetch('/api/delete-hour/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ date: dateStr, hour: activeHour })
    });
    const data = await res.json();
    if (data.status === 'success') {
      showiOSToast('Cleared', '✓');
      closeLogModal();
      setTimeout(() => { window.location.reload(); }, 250);
    }
  } catch (err) {
    console.error('Error deleting hour:', err);
  }
}

// --- Motivational Quotes Engine ---
async function fetchNewQuote() {
  const quoteText = document.getElementById('quoteText');
  const quoteAuthor = document.getElementById('quoteAuthor');
  const quoteTag = document.getElementById('quoteTag');

  if (quoteText) quoteText.style.opacity = '0.2';

  try {
    const res = await fetch('/api/quote/');
    const data = await res.json();
    if (data.status === 'success') {
      setTimeout(() => {
        if (quoteText) {
          quoteText.innerText = `"${data.quote.quote}"`;
          quoteText.style.opacity = '1';
        }
        if (quoteAuthor) quoteAuthor.innerText = `— ${data.quote.author}`;
        if (quoteTag) quoteTag.innerText = data.quote.tag;
      }, 160);
    }
  } catch (e) {
    console.error('Failed to fetch quote', e);
  }
}

// --- Assistant Drawer ---
class AIAssistant {
  constructor() {
    this.panel = document.getElementById('assistantPanel');
    this.openBtn = document.getElementById('siriFloatBtn');
    this.topBarAiBtn = document.getElementById('topBarAiBtn');
    this.tabAssistantBtn = document.getElementById('tabAssistantBtn');
    this.closeBtn = document.getElementById('assistantCloseBtn');
    this.messagesContainer = document.getElementById('assistantMessages');
    this.input = document.getElementById('assistantInput');
    this.sendBtn = document.getElementById('assistantSendBtn');
    this.floatingDock = document.getElementById('aiFloatingDock');
    this.hideDockBtn = document.getElementById('aiDockHideBtn');

    if (this.openBtn) {
      this.openBtn.addEventListener('click', () => this.toggle());
    }
    if (this.topBarAiBtn) {
      this.topBarAiBtn.addEventListener('click', () => this.toggle());
    }
    if (this.tabAssistantBtn) {
      this.tabAssistantBtn.addEventListener('click', () => this.toggle());
    }
    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.close());
    }
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this.sendMessage());
    }
    if (this.input) {
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.sendMessage();
      });
    }

    // Floating Dock hide/show persistence
    if (this.hideDockBtn && this.floatingDock) {
      const isDockHidden = localStorage.getItem('ios_ai_dock_hidden') === 'true';
      if (isDockHidden) {
        this.floatingDock.classList.add('is-hidden');
      }

      this.hideDockBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.floatingDock.classList.add('is-hidden');
        localStorage.setItem('ios_ai_dock_hidden', 'true');
      });
    }

    // ESC key closes assistant
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.panel && this.panel.classList.contains('open')) {
        this.close();
      }
    });

    document.querySelectorAll('.suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const text = chip.getAttribute('data-prompt') || chip.innerText;
        if (this.input) this.input.value = text;
        this.sendMessage();
      });
    });
  }

  toggle() {
    if (!this.panel) return;
    this.panel.classList.toggle('open');
    if (this.panel.classList.contains('open')) {
      if (this.input) this.input.focus();
      this.scrollToBottom();
    }
  }

  close() {
    if (this.panel) this.panel.classList.remove('open');
  }

  scrollToBottom() {
    if (this.messagesContainer) {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
  }

  appendBubble(text, sender = 'user') {
    if (!this.messagesContainer) return;
    const bubble = document.createElement('div');
    bubble.className = `msg-bubble msg-${sender}`;

    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n•/g, '<br>•')
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');

    bubble.innerHTML = formatted;
    this.messagesContainer.appendChild(bubble);
    this.scrollToBottom();
  }

  async sendMessage() {
    if (!this.input) return;
    const text = this.input.value.trim();
    if (!text) return;

    this.appendBubble(text, 'user');
    this.input.value = '';

    const typingBubble = document.createElement('div');
    typingBubble.className = 'msg-bubble msg-assistant';
    typingBubble.id = 'typingBubble';
    typingBubble.innerHTML = '<em>Thinking...</em>';
    this.messagesContainer.appendChild(typingBubble);
    this.scrollToBottom();

    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      typingBubble.remove();

      if (data.status === 'success') {
        this.appendBubble(data.reply, 'assistant');
        iOSAudio.playChime('success');

        if (data.action_type === 'set_reminder') {
          showiOSToast('Reminder scheduled', '✓');
        }
      } else {
        this.appendBubble("Sorry, unable to process right now.", 'assistant');
      }
    } catch (e) {
      typingBubble.remove();
      this.appendBubble("Network issue. Please retry.", 'assistant');
      console.error(e);
    }
  }
}

// --- Reminders Service ---
class ReminderService {
  constructor() {
    this.interval = null;
    this.start();
  }

  start() {
    this.check();
    this.interval = setInterval(() => this.check(), 30000);
  }

  async check() {
    try {
      const res = await fetch('/api/reminders/check/');
      const data = await res.json();
      if (data.status === 'success' && data.due_reminders && data.due_reminders.length > 0) {
        data.due_reminders.forEach(r => {
          iOSAudio.playChime('reminder');
          showiOSToast(`${r.title} (${r.time_display})`, '✓');
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Habit Reminder", {
              body: `${r.title} — Time to review your hour!`,
            });
          }
        });
      }
    } catch (e) {}
  }
}

// --- Theme Controller ---
function initTheme() {
  const savedTheme = localStorage.getItem('ios_habit_theme') || 'system';
  applyTheme(savedTheme);

  const toggleBtn = document.getElementById('themeToggleBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem('ios_habit_theme', next);
    });
  }
}

function applyTheme(theme) {
  let effective = theme;
  if (theme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    effective = prefersDark ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', effective);

  // Smooth Apple SF Symbol morph for Sun/Moon
  const slot = document.querySelector('#themeToggleBtn .theme-icon-slot');
  if (slot) {
    if (effective === 'dark') {
      slot.innerHTML = `<svg class="sf-icon sf-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    } else {
      slot.innerHTML = `<svg class="sf-icon sf-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    }
  }
}

// --- Apple Account Popover Menu ---
function initAccountMenu() {
  const menuWrapper = document.querySelector('.apple-account-menu-wrapper');
  const menuBtn = document.getElementById('accountMenuBtn');
  const popover = document.getElementById('accountPopover');

  if (!menuBtn || !popover) return;

  const togglePopover = (forceState) => {
    const isHidden = typeof forceState === 'boolean' ? !forceState : !popover.hidden;
    popover.hidden = isHidden;
    menuBtn.setAttribute('aria-expanded', String(!isHidden));
    if (menuWrapper) {
      menuWrapper.classList.toggle('active', !isHidden);
    }
  };

  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePopover();
  });

  document.addEventListener('click', (e) => {
    if (!popover.hidden && menuWrapper && !menuWrapper.contains(e.target)) {
      togglePopover(false);
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !popover.hidden) {
      togglePopover(false);
    }
  });
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initAccountMenu();

  const isAuthenticated = !!document.getElementById('currentDateStr') || !!document.querySelector('.ios-nav');
  if (isAuthenticated) {
    new HabitTimer();
    new AIAssistant();
    new ReminderService();

    if ("Notification" in window && Notification.permission === "default") {
      setTimeout(() => {
        Notification.requestPermission();
      }, 4000);
    }
  }

  document.querySelectorAll('.category-tile').forEach(tile => {
    tile.addEventListener('click', () => {
      document.querySelectorAll('.category-tile').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');
      selectedCategory = tile.dataset.catId;
    });
  });

  document.querySelectorAll('.segmented-option').forEach(opt => {
    opt.addEventListener('click', () => {
      setModalUnit(opt.dataset.unit);
    });
  });

  document.querySelectorAll('.energy-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      setModalEnergy(parseInt(dot.dataset.level));
    });
  });

  const refreshQuoteBtn = document.getElementById('refreshQuoteBtn');
  if (refreshQuoteBtn) {
    refreshQuoteBtn.addEventListener('click', fetchNewQuote);
  }
});
