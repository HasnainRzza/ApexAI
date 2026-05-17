let userTab = 'lecturers';
let semestersCache = [];
let coursesCache = [];
let lecturersCache = [];
let studentsCache = [];

document.querySelectorAll('.nav-item').forEach((btn) => {
  btn.addEventListener('click', () => UI.showPanel(btn.dataset.panel));
});

document.querySelectorAll('.modal-close').forEach((btn) => {
  btn.addEventListener('click', () => UI.closeModal(btn.dataset.modal));
});

document.querySelectorAll('[data-user-tab]').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-user-tab]').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    userTab = btn.dataset.userTab;
    loadUsers();
  });
});

document.getElementById('btn-add-course')?.addEventListener('click', () => {
  fillSemesterSelect('course-semester-select');
  UI.openModal('modal-course');
});

document.getElementById('btn-add-semester')?.addEventListener('click', () => UI.openModal('modal-semester'));
document.getElementById('btn-add-user')?.addEventListener('click', () => {
  document.getElementById('modal-user-title').textContent =
    userTab === 'lecturers' ? 'Add Lecturer' : 'Add Student';
  UI.openModal('modal-user');
});
document.getElementById('btn-assign-lecturer')?.addEventListener('click', openAllocationModal);
document.getElementById('btn-enroll-student')?.addEventListener('click', openEnrollmentModal);

document.getElementById('course-search')?.addEventListener('input', (e) => loadCourses(e.target.value));

document.getElementById('form-course')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await API.admin.createCourse({
      code: fd.get('code'),
      name: fd.get('name'),
      semester_id: Number(fd.get('semester_id')),
    });
    UI.toast('Course created', 'success');
    UI.closeModal('modal-course');
    e.target.reset();
    loadCourses();
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

document.getElementById('form-semester')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await API.admin.createSemester({
      name: fd.get('name'),
      year: Number(fd.get('year')),
      term: fd.get('term'),
    });
    UI.toast('Semester created', 'success');
    UI.closeModal('modal-semester');
    e.target.reset();
    loadSemesters();
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

document.getElementById('form-user')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    first_name: fd.get('first_name'),
    last_name: fd.get('last_name'),
    email: fd.get('email'),
    password: fd.get('password') || undefined,
  };
  try {
    const fn = userTab === 'lecturers' ? API.admin.createLecturer : API.admin.createStudent;
    const res = await fn(body);
    document.getElementById('creds-content').innerHTML =
      `<p>Email: ${UI.esc(res.email)}</p><p>Password: ${UI.esc(res.password)}</p>`;
    UI.closeModal('modal-user');
    UI.openModal('modal-creds');
    e.target.reset();
    loadUsers();
    if (userTab === 'lecturers') loadLecturersCache();
    else loadStudentsCache();
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

document.getElementById('form-allocation')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await API.admin.assignLecturer({
      lecturer_id: Number(fd.get('lecturer_id')),
      course_id: Number(fd.get('course_id')),
    });
    UI.toast('Lecturer assigned', 'success');
    UI.closeModal('modal-allocation');
    loadAllocations();
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

document.getElementById('form-enrollment')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await API.admin.enroll({
      student_id: Number(fd.get('student_id')),
      course_id: Number(fd.get('course_id')),
      semester_id: Number(fd.get('semester_id')),
    });
    UI.toast('Student enrolled', 'success');
    UI.closeModal('modal-enrollment');
    loadEnrollments();
  } catch (err) {
    UI.toast(err.message, 'error');
  }
});

async function loadDashboard() {
  try {
    const s = await API.admin.dashboard();
    document.getElementById('stats-grid').innerHTML = `
      <article class="stat-card"><p class="label">Students</p><p class="value">${s.total_students}</p></article>
      <article class="stat-card"><p class="label">Lecturers</p><p class="value">${s.total_lecturers}</p></article>
      <article class="stat-card"><p class="label">Courses</p><p class="value">${s.total_courses}</p></article>
      <article class="stat-card"><p class="label">Quizzes</p><p class="value">${s.total_quizzes}</p></article>
      <article class="stat-card"><p class="label">Active Quizzes</p><p class="value">${s.active_quizzes}</p></article>`;
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadSemesters() {
  try {
    semestersCache = await API.admin.semesters();
    UI.renderTable('semesters-table', [
      { key: 'name', label: 'Name' },
      { key: 'year', label: 'Year' },
      { key: 'term', label: 'Term' },
    ], semestersCache, (row) =>
      `<button class="btn btn-danger btn-sm" data-del-semester="${row.id}">Delete</button>`);
    document.querySelectorAll('[data-del-semester]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Delete this semester?')) return;
        try {
          await API.admin.deleteSemester(b.dataset.delSemester);
          UI.toast('Deleted', 'success');
          loadSemesters();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

function fillSemesterSelect(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = semestersCache.map((s) =>
    `<option value="${s.id}">${UI.esc(s.name)} (${s.year})</option>`).join('');
}

async function loadCourses(q = '') {
  try {
    coursesCache = await API.admin.courses(q);
    UI.renderTable('courses-table', [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'semester_name', label: 'Semester' },
    ], coursesCache, (row) =>
      `<button class="btn btn-danger btn-sm" data-del-course="${row.id}">Delete</button>`);
    document.querySelectorAll('[data-del-course]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Delete course and related allocations?')) return;
        try {
          await API.admin.deleteCourse(b.dataset.delCourse);
          UI.toast('Deleted', 'success');
          loadCourses(document.getElementById('course-search')?.value || '');
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadLecturersCache() {
  lecturersCache = await API.admin.lecturers();
}

async function loadStudentsCache() {
  studentsCache = await API.admin.students();
}

async function loadUsers() {
  try {
    if (userTab === 'lecturers') await loadLecturersCache();
    else await loadStudentsCache();
    const rows = userTab === 'lecturers' ? lecturersCache : studentsCache;
    const codeKey = userTab === 'lecturers' ? 'employee_code' : 'student_code';
    UI.renderTable('users-table', [
      { key: 'first_name', label: 'First' },
      { key: 'last_name', label: 'Last' },
      { key: 'email', label: 'Email' },
      { key: codeKey, label: 'Code' },
    ], rows, (row) =>
      `<button class="btn btn-danger btn-sm" data-del-user="${row.id}" data-type="${userTab}">Delete</button>`);
    document.querySelectorAll('[data-del-user]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Delete this user?')) return;
        const fn = b.dataset.type === 'lecturers' ? API.admin.deleteLecturer : API.admin.deleteStudent;
        try {
          await fn(b.dataset.delUser);
          UI.toast('Deleted', 'success');
          loadUsers();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadAllocations() {
  try {
    const rows = await API.admin.allocations();
    UI.renderTable('allocations-table', [
      { key: 'lecturer_name', label: 'Lecturer' },
      { key: 'code', label: 'Course Code' },
      { key: 'course_name', label: 'Course' },
    ], rows, (row) =>
      `<button class="btn btn-danger btn-sm" data-del-alloc="${row.id}">Remove</button>`);
    document.querySelectorAll('[data-del-alloc]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Remove allocation?')) return;
        try {
          await API.admin.removeAllocation(b.dataset.delAlloc);
          UI.toast('Removed', 'success');
          loadAllocations();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadEnrollments() {
  try {
    const rows = await API.admin.enrollments();
    UI.renderTable('enrollments-table', [
      { key: 'student_name', label: 'Student' },
      { key: 'email', label: 'Email' },
      { key: 'course_code', label: 'Course' },
    ], rows, (row) =>
      `<button class="btn btn-danger btn-sm" data-del-enroll="${row.id}">Remove</button>`);
    document.querySelectorAll('[data-del-enroll]').forEach((b) => {
      b.addEventListener('click', async () => {
        if (!UI.confirm('Remove enrollment?')) return;
        try {
          await API.admin.removeEnrollment(b.dataset.delEnroll);
          UI.toast('Removed', 'success');
          loadEnrollments();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      });
    });
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function loadQuizzes() {
  try {
    const rows = await API.admin.quizzes();
    UI.renderTable('quizzes-table', [
      { key: 'title', label: 'Title' },
      { key: 'course_code', label: 'Course' },
      { key: 'lecturer_name', label: 'Lecturer' },
      { key: 'start_time', label: 'Start', render: (r) => UI.formatDate(r.start_time) },
      { key: 'end_time', label: 'End', render: (r) => UI.formatDate(r.end_time) },
    ], rows);
  } catch (err) {
    UI.toast(err.message, 'error');
  }
}

async function openAllocationModal() {
  await Promise.all([loadLecturersCache(), loadCourses()]);
  const lsel = document.getElementById('alloc-lecturer-select');
  const csel = document.getElementById('alloc-course-select');
  lsel.innerHTML = lecturersCache.map((l) =>
    `<option value="${l.id}">${UI.esc(l.first_name)} ${UI.esc(l.last_name)}</option>`).join('');
  csel.innerHTML = coursesCache.map((c) =>
    `<option value="${c.id}">${UI.esc(c.code)} - ${UI.esc(c.name)}</option>`).join('');
  UI.openModal('modal-allocation');
}

async function openEnrollmentModal() {
  await Promise.all([loadStudentsCache(), loadCourses(), loadSemesters()]);
  document.getElementById('enroll-student-select').innerHTML = studentsCache.map((s) =>
    `<option value="${s.id}">${UI.esc(s.first_name)} ${UI.esc(s.last_name)}</option>`).join('');
  document.getElementById('enroll-course-select').innerHTML = coursesCache.map((c) =>
    `<option value="${c.id}">${UI.esc(c.code)}</option>`).join('');
  fillSemesterSelect('enroll-semester-select');
  UI.openModal('modal-enrollment');
}

async function init() {
  await loadSemesters();
  loadDashboard();
  loadCourses();
  loadUsers();
  loadAllocations();
  loadEnrollments();
  loadQuizzes();
}

init();
