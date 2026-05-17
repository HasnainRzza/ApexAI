let courses = [];
let questionCount = 0;

document.querySelectorAll('.nav-item').forEach((btn) => {
  btn.addEventListener('click', () => UI.showPanel(btn.dataset.panel));
});

document.getElementById('btn-add-question')?.addEventListener('click', () => addQuestionBlock());

function addQuestionBlock(data) {
  questionCount += 1;
  const id = questionCount;
  const container = document.getElementById('questions-container');
  const block = document.createElement('div');
  block.className = 'question-editor';
  block.dataset.qid = id;
  const opts = (data?.options || [
    { text: '', is_correct: true },
    { text: '' },
    { text: '' },
    { text: '' },
  ]).map((o, i) => optionRow(id, i, o.text, o.is_correct)).join('');
  block.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem">
      <strong>Question ${id}</strong>
      <button type="button" class="btn btn-danger btn-sm" data-remove-q="${id}">Remove</button>
    </div>
    <div class="form-group">
      <label>Statement</label>
      <textarea name="q_statement_${id}" rows="2" required>${UI.esc(data?.statement || '')}</textarea>
    </div>
    <div class="options-list" data-qid="${id}">${opts}</div>
    <button type="button" class="btn btn-ghost btn-sm" data-add-opt="${id}" style="margin-top:0.5rem">+ Option</button>`;
  container.appendChild(block);
  block.querySelector(`[data-remove-q="${id}"]`)?.addEventListener('click', () => block.remove());
  block.querySelector(`[data-add-opt="${id}"]`)?.addEventListener('click', () => {
    const list = block.querySelector('.options-list');
    const idx = list.querySelectorAll('.option-row').length;
    list.insertAdjacentHTML('beforeend', optionRow(id, idx, '', false));
  });
}

function optionRow(qid, idx, text, correct) {
  return `<div class="option-row form-row" style="align-items:center;margin-top:0.5rem">
    <div class="form-group" style="flex:1;margin:0">
      <input name="q_${qid}_opt_${idx}" value="${UI.esc(text)}" placeholder="Option ${idx + 1}" required />
    </div>
    <label style="display:flex;align-items:center;gap:0.35rem;white-space:nowrap">
      <input type="radio" name="q_${qid}_correct" value="${idx}" ${correct ? 'checked' : ''} required /> Correct
    </label>
  </div>`;
}

function collectQuestions() {
  const blocks = document.querySelectorAll('.question-editor');
  const questions = [];
  blocks.forEach((block) => {
    const id = block.dataset.qid;
    const statement = block.querySelector(`[name="q_statement_${id}"]`)?.value.trim();
    const correctIdx = block.querySelector(`[name="q_${id}_correct"]:checked`)?.value;
    const inputs = block.querySelectorAll(`[name^="q_${id}_opt_"]`);
    const options = [];
    inputs.forEach((inp, i) => {
      const text = inp.value.trim();
      if (text) options.push({ text, is_correct: String(i) === correctIdx });
    });
    questions.push({ statement, options });
  });
  return questions;
}

document.getElementById('form-quiz')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    course_id: Number(fd.get('course_id')),
    title: fd.get('title'),
    start_time: fd.get('start_time'),
    end_time: fd.get('end_time'),
    duration_minutes: Number(fd.get('duration_minutes')),
    allow_multiple_attempts: fd.get('allow_multiple_attempts') === 'on',
    questions: collectQuestions(),
  };
  try {
    await API.lecturer.createQuiz(body);
    UI.toast('Quiz created', 'success');
    e.target.reset();
    document.getElementById('questions-container').innerHTML = '';
    questionCount = 0;
    addQuestionBlock();
    loadQuizzes();
    UI.showPanel('panel-quizzes');
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

async function loadCourses() {
  try {
    courses = await API.lecturer.courses();
    const sel = document.getElementById('quiz-course-select');
    if (sel) {
      sel.innerHTML = courses.map((c) =>
        `<option value="${c.id}">${UI.esc(c.code)} - ${UI.esc(c.name)}</option>`).join('');
    }
    UI.renderTable('courses-table', [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'semester_name', label: 'Semester' },
    ], courses);
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadQuizzes() {
  try {
    const rows = await API.lecturer.quizzes();
    UI.renderTable('quizzes-table', [
      { key: 'title', label: 'Title' },
      { key: 'course_code', label: 'Course' },
      { key: 'start_time', label: 'Start', render: (r) => UI.formatDate(r.start_time) },
      { key: 'end_time', label: 'End', render: (r) => UI.formatDate(r.end_time) },
      { key: 'duration_minutes', label: 'Duration (min)' },
    ], rows, (row) => `
      <button class="btn btn-ghost btn-sm" data-view-sub="${row.id}">Submissions</button>
      <button class="btn btn-danger btn-sm" data-del-quiz="${row.id}">Delete</button>`);
    document.querySelectorAll('[data-del-quiz]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Delete this quiz?')) return;
        try {
          await API.lecturer.deleteQuiz(b.dataset.delQuiz);
          UI.toast('Deleted', 'success');
          loadQuizzes();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
    document.querySelectorAll('[data-view-sub]').forEach((b) => {
      b.addEventListener('click', () => loadSubmissions(b.dataset.viewSub));
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadSubmissions(quizId) {
  try {
    const rows = await API.lecturer.submissions(quizId);
    document.getElementById('submissions-panel').classList.remove('hidden');
    UI.renderTable('submissions-table', [
      { key: 'first_name', label: 'First' },
      { key: 'last_name', label: 'Last' },
      { key: 'email', label: 'Email' },
      { key: 'score', label: 'Score', render: (r) => r.score != null ? `${r.score}%` : '-' },
      { key: 'status', label: 'Status' },
      { key: 'submitted_at', label: 'Submitted', render: (r) => UI.formatDate(r.submitted_at) },
    ], rows);
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

loadCourses();
loadQuizzes();
addQuestionBlock();
