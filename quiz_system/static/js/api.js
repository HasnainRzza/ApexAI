const API = {
  async request(path, options = {}) {
    const res = await fetch(path, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
  },

  login(email, password) {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  logout() {
    return this.request('/api/auth/logout', { method: 'POST' });
  },

  me() {
    return this.request('/api/auth/me');
  },

  admin: {
    dashboard: () => API.request('/api/admin/dashboard'),
    semesters: () => API.request('/api/admin/semesters'),
    createSemester: (body) => API.request('/api/admin/semesters', { method: 'POST', body: JSON.stringify(body) }),
    deleteSemester: (id) => API.request(`/api/admin/semesters/${id}`, { method: 'DELETE' }),
    courses: (q) => API.request(`/api/admin/courses${q ? `?q=${encodeURIComponent(q)}` : ''}`),
    createCourse: (body) => API.request('/api/admin/courses', { method: 'POST', body: JSON.stringify(body) }),
    deleteCourse: (id) => API.request(`/api/admin/courses/${id}`, { method: 'DELETE' }),
    lecturers: () => API.request('/api/admin/lecturers'),
    createLecturer: (body) => API.request('/api/admin/lecturers', { method: 'POST', body: JSON.stringify(body) }),
    deleteLecturer: (id) => API.request(`/api/admin/lecturers/${id}`, { method: 'DELETE' }),
    students: () => API.request('/api/admin/students'),
    createStudent: (body) => API.request('/api/admin/students', { method: 'POST', body: JSON.stringify(body) }),
    deleteStudent: (id) => API.request(`/api/admin/students/${id}`, { method: 'DELETE' }),
    allocations: () => API.request('/api/admin/allocations'),
    assignLecturer: (body) => API.request('/api/admin/allocations', { method: 'POST', body: JSON.stringify(body) }),
    removeAllocation: (id) => API.request(`/api/admin/allocations?id=${id}`, { method: 'DELETE' }),
    enrollments: () => API.request('/api/admin/enrollments'),
    enroll: (body) => API.request('/api/admin/enrollments', { method: 'POST', body: JSON.stringify(body) }),
    removeEnrollment: (id) => API.request(`/api/admin/enrollments?id=${id}`, { method: 'DELETE' }),
    quizzes: () => API.request('/api/admin/quizzes'),
  },

  lecturer: {
    courses: () => API.request('/api/lecturer/courses'),
    quizzes: () => API.request('/api/lecturer/quizzes'),
    createQuiz: (body) => API.request('/api/lecturer/quizzes', { method: 'POST', body: JSON.stringify(body) }),
    getQuiz: (id) => API.request(`/api/lecturer/quizzes/${id}`),
    deleteQuiz: (id) => API.request(`/api/lecturer/quizzes/${id}`, { method: 'DELETE' }),
    submissions: (id) => API.request(`/api/lecturer/quizzes/${id}/submissions`),
  },

  student: {
    courses: () => API.request('/api/student/courses'),
    quizzes: () => API.request('/api/student/quizzes'),
    allQuizzes: () => API.request('/api/student/quizzes/all'),
    startQuiz: (id) => API.request(`/api/student/quizzes/${id}/start`, { method: 'POST' }),
    submit: (aid, answers, auto) =>
      API.request(`/api/student/attempts/${aid}/submit`, {
        method: 'POST',
        body: JSON.stringify({ answers, auto_submit: auto }),
      }),
  },
};
