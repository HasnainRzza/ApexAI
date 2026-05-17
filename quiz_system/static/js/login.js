document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = 'Signing in...';
  try {
    await API.logout().catch(() => {});
    const data = await API.login(
      document.getElementById('email').value.trim(),
      document.getElementById('password').value,
    );
    const role = data.user.role_name;
    window.location.href = role === 'admin' ? '/admin' : role === 'lecturer' ? '/lecturer' : '/student';
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
    btn.disabled = false;
    btn.textContent = 'Sign in';
  }
});
