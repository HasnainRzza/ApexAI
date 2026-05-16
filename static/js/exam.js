/* =====================================================
   ApexAI — Exam page client-side logic
   ===================================================== */

const socket = io({ transports: ['websocket'] });

// ---- DOM refs ----
const video      = document.getElementById('video');
const canvas     = document.getElementById('canvas');
const ctx        = canvas.getContext('2d');
const camOverlay = document.getElementById('cam-overlay');
const camStatus  = document.getElementById('cam-status');
const connDot    = document.getElementById('connection-dot');
const fpsDisplay = document.getElementById('fps-display');
const sidDisplay = document.getElementById('session-id-display');

let screenStream = null;
const screenVideo = document.createElement('video');
const screenCanvas = document.createElement('canvas');
const sctx = screenCanvas.getContext('2d');

// Dashboard
const scoreVal      = document.getElementById('score-value');
const scoreArc      = document.getElementById('score-arc');
const severityBadge = document.getElementById('severity-badge');
const cheatBanner   = document.getElementById('cheating-banner');

const cards = {
  face:    document.getElementById('card-face'),
  multi:   document.getElementById('card-multi'),
  head:    document.getElementById('card-head'),
  gaze:    document.getElementById('card-gaze'),
  audio:   document.getElementById('card-audio'),
  object:  document.getElementById('card-object'),
  browser: document.getElementById('card-browser'),
};
const stats = {
  face:    document.getElementById('stat-face'),
  multi:   document.getElementById('stat-multi'),
  head:    document.getElementById('stat-head'),
  gaze:    document.getElementById('stat-gaze'),
  audio:   document.getElementById('stat-audio'),
  object:  document.getElementById('stat-object'),
  browser: document.getElementById('stat-browser'),
};
const eventLog = document.getElementById('event-log');

// ---- Config ----
const FPS_TARGET      = 10;        // frames/sec sent to server
const AUDIO_RATE      = 16000;
const FRAME_INTERVAL  = 1000 / FPS_TARGET;
const ARC_CIRC        = 327;       // 2 * pi * 52

let lastFrameTime = 0;
let frameCount    = 0;
let fpsInterval   = setInterval(() => {
  fpsDisplay.textContent = `${frameCount} FPS`;
  frameCount = 0;
}, 1000);

// ---- Socket events ----
socket.on('connect', () => {
  connDot.className = 'dot dot-green';
});
socket.on('disconnect', () => {
  connDot.className = 'dot dot-red';
});
socket.on('connected', (data) => {
  sidDisplay.textContent = `Session: ${data.exam_session.slice(0,8)}`;
});

socket.on('state_update', (d) => {
  // Score ring
  const pct    = Math.min(d.score / 100, 1);
  const offset = ARC_CIRC - pct * ARC_CIRC;
  scoreArc.style.strokeDashoffset = offset;
  scoreArc.style.stroke = pct > 0.8 ? '#ef4444' : pct > 0.5 ? '#f59e0b' : '#6C63FF';
  scoreVal.textContent  = Math.round(d.score);

  // Severity badge
  const sev = d.severity.toLowerCase();
  severityBadge.textContent  = d.severity;
  severityBadge.className    = `severity-badge sev-${sev}`;

  // Cheating banner
  if (d.is_cheating) cheatBanner.classList.remove('hidden');

  // Stat cards helper
  function setCard(key, ok, text) {
    cards[key].className = `stat-card ${ok ? 'ok' : 'bad'}`;
    stats[key].textContent = text;
    stats[key].className   = `stat-val ${ok ? 'val-ok' : 'val-bad'}`;
  }

  setCard('face',    !d.face_missing,       d.face_missing ? 'Missing' : 'Present');
  setCard('multi',   !d.multiple_faces,      d.multiple_faces ? 'Detected!' : 'No');
  setCard('head',    !d.head_anomaly,        d.head_dir);
  setCard('gaze',    !d.gaze_anomaly,        d.gaze_dir);
  setCard('audio',   !d.audio_anomaly,       d.audio_anomaly ? 'Speech!' : 'Normal');
  setCard('object',  !d.object_detected,     d.object_detected ? d.objects.map(o=>o.class).join(', ') : 'None');
  setCard('browser', !d.browser_violation,   d.browser_violation ? 'Tab Switch!' : 'OK');

  // Event log
  const bad = ['face_missing','multiple_faces','object_detected','browser_violation']
    .filter(k => d[k]);
  if (d.is_cheating) bad.push('cheating');
  if (bad.length) {
    const entry = document.createElement('div');
    entry.className = `event-entry ${d.is_cheating ? 'bad' : ''}`;
    entry.textContent = `${new Date().toLocaleTimeString()} — ${bad.join(', ')}`;
    eventLog.prepend(entry);
    if (eventLog.children.length > 30) eventLog.lastChild.remove();
  }
});

// ---- Camera & frame streaming ----
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width:640, height:480 }, audio: true });
    video.srcObject = stream;
    video.onloadedmetadata = () => {
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      camOverlay.classList.add('hidden');
      requestAnimationFrame(sendFrame);
    };
    startAudio(stream);
  } catch (err) {
    camStatus.textContent = `Camera error: ${err.message}`;
  }
}

function sendFrame(ts) {
  requestAnimationFrame(sendFrame);
  if (ts - lastFrameTime < FRAME_INTERVAL) return;
  lastFrameTime = ts;
  if (!socket.connected) return;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const b64 = canvas.toDataURL('image/jpeg', 0.6);
  socket.emit('video_frame', { frame: b64 });
  frameCount++;
}

// ---- Audio streaming ----
function startAudio(stream) {
  try {
    const audioCtx = new AudioContext({ sampleRate: AUDIO_RATE });
    const src = audioCtx.createMediaStreamSource(stream);
    const proc = audioCtx.createScriptProcessor(480, 1, 1);  // 30ms at 16kHz

    proc.onaudioprocess = (e) => {
      if (!socket.connected) return;
      const f32 = e.inputBuffer.getChannelData(0);
      // Convert float32 -> int16
      const i16 = new Int16Array(f32.length);
      for (let i = 0; i < f32.length; i++) {
        i16[i] = Math.max(-32768, Math.min(32767, f32[i] * 32768));
      }
      socket.emit('audio_chunk', { pcm: Array.from(new Uint8Array(i16.buffer)) });
    };

    src.connect(proc);
    proc.connect(audioCtx.destination);
  } catch (err) {
    console.warn('Audio init failed:', err);
  }
}

// ---- Browser focus monitoring ----
window.addEventListener('blur', () => handleBrowserViolation('blur'));
document.addEventListener('visibilitychange', () => {
  if (document.hidden) handleBrowserViolation('hidden');
  else socket.emit('browser_event', { type: 'visible' });
});

window.addEventListener('focus', ()  => socket.emit('browser_event', { type: 'focus' }));

document.addEventListener('fullscreenchange', () => {
  socket.emit('browser_event', { type: document.fullscreenElement ? 'fullscreen_enter' : 'fullscreen_exit' });
});

function handleBrowserViolation(type) {
  console.log(`[Browser Violation] Triggered by: ${type}`);
  socket.emit('browser_event', { type: type });
  
  // Capture screen content as proof
  if (screenStream && screenStream.active) {
    try {
      sctx.drawImage(screenVideo, 0, 0, screenCanvas.width, screenCanvas.height);
      const b64 = screenCanvas.toDataURL('image/jpeg', 0.7);
      socket.emit('browser_screen_capture', { frame: b64 });
      console.log("[Browser Violation] Screen captured and sent.");
    } catch (e) {
      console.error("[Browser Violation] Screen capture failed:", e);
    }
  } else {
    console.warn("[Browser Violation] No active screen stream to capture.");
  }
}

// ---- Boot ----
async function boot() {
  camStatus.textContent = "Please share your ENTIRE SCREEN to continue...";
  try {
    screenStream = await navigator.mediaDevices.getDisplayMedia({ 
      video: { cursor: "always" }, 
      audio: false 
    });
    
    screenVideo.srcObject = screenStream;
    screenVideo.autoplay = true;
    screenVideo.playsInline = true;
    screenVideo.muted = true;
    
    await screenVideo.play();
    
    screenCanvas.width = screenVideo.videoWidth;
    screenCanvas.height = screenVideo.videoHeight;
    
    // If user stops sharing, we should ideally block the exam
    screenStream.getVideoTracks()[0].onended = () => {
      alert("Screen sharing is required for the exam!");
      window.location.reload();
    };
    
    await startCamera();
  } catch (err) {
    camStatus.textContent = "Screen sharing is MANDATORY. Please refresh and allow.";
    console.error("Boot error:", err);
  }
}

boot();
