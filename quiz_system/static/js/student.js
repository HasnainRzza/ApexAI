document.querySelectorAll('.nav-item').forEach((btn) => {
  btn.addEventListener('click', () => UI.showPanel(btn.dataset.panel));
});

async function loadCourses() {
  try {
    const rows = await API.student.courses();
    UI.renderTable('courses-table', [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'semester_name', label: 'Semester' },
    ], rows);
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadActive() {
  const el = document.getElementById('active-quizzes');
  try {
    const rows = await API.student.quizzes();
    if (!rows.length) {
      el.innerHTML = '<p class="empty-state">No active quizzes right now.</p>';
      return;
    }
    el.innerHTML = rows.map((q) => {
      const done = q.already_submitted;
      return `<article class="card" style="margin-bottom:1rem">
        <h2 style="color:var(--text);margin-bottom:0.5rem">${UI.esc(q.title)}</h2>
        <p style="color:var(--muted);font-size:0.9rem">${UI.esc(q.course_code)} · ${q.duration_minutes} min</p>
        <p style="font-size:0.85rem;margin:0.5rem 0">${UI.formatDate(q.start_time)} — ${UI.formatDate(q.end_time)}</p>
        ${done
          ? `<span class="badge">Submitted · Score: ${q.score != null ? q.score + '%' : 'pending'}</span>`
          : `<a href="/student/quiz/${q.id}" class="btn btn-primary" style="margin-top:0.75rem">Start Quiz</a>`}
      </article>`;
    }).join('');
  } catch (err) {
    el.innerHTML = `<p class="error-text">${UI.esc(err.message)}</p>`;
  }
}

async function loadHistory() {
  try {
    const rows = await API.student.allQuizzes();
    UI.renderTable('history-table', [
      { key: 'title', label: 'Title' },
      { key: 'course_code', label: 'Course' },
      { key: 'start_time', label: 'Start', render: (r) => UI.formatDate(r.start_time) },
      { key: 'attempt_status', label: 'Status', render: (r) => r.attempt_status || 'Not attempted' },
      { key: 'score', label: 'Score', render: (r) => (r.score != null ? `${r.score}%` : '-') },
    ], rows, (row) =>
      !row.attempt_status || row.attempt_status === 'in_progress'
        ? `<a href="/student/quiz/${row.id}" class="btn btn-primary btn-sm">Open</a>`
        : '');
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

loadCourses();
loadActive();
loadHistory();
