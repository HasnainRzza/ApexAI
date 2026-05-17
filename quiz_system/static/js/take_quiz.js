const quizId = window.QUIZ_ID;
let attemptId = null;
let timerInterval = null;
let expiresAt = null;

async function init() {
  try {
    const data = await API.student.startQuiz(quizId);
    attemptId = data.attempt.id;
    const quiz = data.quiz;
    expiresAt = new Date(data.expires_at).getTime();

    document.getElementById('quiz-title').textContent = quiz.title;
    document.getElementById('quiz-loading').classList.add('hidden');
    document.getElementById('quiz-timer').classList.remove('hidden');

    const form = document.getElementById('quiz-form');
    form.classList.remove('hidden');
    form.innerHTML = quiz.questions.map((q, qi) => `
      <article class="question-block" data-qid="${q.id}">
        <p><strong>Q${qi + 1}.</strong> ${UI.esc(q.statement)}</p>
        ${q.options.map((o) => `
          <label class="option-label">
            <input type="radio" name="q_${q.id}" value="${o.id}" required />
            <span>${UI.esc(o.option_text)}</span>
          </label>`).join('')}
      </article>`).join('') + `
      <button type="submit" class="btn btn-primary" style="margin-top:1rem">Submit Quiz</button>`;

    form.addEventListener('submit', onSubmit);
    startTimer();
  } catch (err) {
    document.getElementById('quiz-loading').textContent = err.message;
    document.getElementById('quiz-loading').classList.add('error-text');
  }
}

function startTimer() {
  const el = document.getElementById('timer-display');
  const box = document.getElementById('quiz-timer');

  function tick() {
    const now = Date.now();
    const left = Math.max(0, expiresAt - now);
    const m = Math.floor(left / 60000);
    const s = Math.floor((left % 60000) / 1000);
    el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    box.classList.toggle('warning', left < 300000 && left > 60000);
    box.classList.toggle('danger', left <= 60000);
    if (left <= 0) {
      clearInterval(timerInterval);
      autoSubmit();
    }
  }
  tick();
  timerInterval = setInterval(tick, 1000);
}

function collectAnswers() {
  const answers = [];
  document.querySelectorAll('.question-block').forEach((block) => {
    const qid = Number(block.dataset.qid);
    const selected = block.querySelector('input[type="radio"]:checked');
    if (selected) {
      answers.push({ question_id: qid, selected_option_id: Number(selected.value) });
    }
  });
  return answers;
}

async function onSubmit(e) {
  e.preventDefault();
  if (!UI.confirm('Submit your answers?')) return;
  await doSubmit(false);
}

async function autoSubmit() {
  UI.toast('Time is up — submitting automatically', 'info');
  await doSubmit(true);
}

async function doSubmit(auto) {
  clearInterval(timerInterval);
  try {
    const result = await API.student.submit(attemptId, collectAnswers(), auto);
    document.getElementById('quiz-form').classList.add('hidden');
    document.getElementById('quiz-timer').classList.add('hidden');
    const res = document.getElementById('quiz-result');
    res.classList.remove('hidden');
    res.innerHTML = `
      <h2>Quiz Submitted</h2>
      <p style="font-size:1.5rem;margin:1rem 0">Your score: <strong>${result.score}%</strong></p>
      <p style="color:var(--muted)">Status: ${UI.esc(result.status)}</p>
      <a href="/student" class="btn btn-primary" style="margin-top:1rem">Back to dashboard</a>`;
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

init();
