const UI = {
  toast(msg, type = 'info') {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  },

  openModal(id) {
    document.getElementById(id)?.classList.add('open');
  },

  closeModal(id) {
    document.getElementById(id)?.classList.remove('open');
  },

  confirm(message) {
    return window.confirm(message);
  },

  esc(s) {
    if (s == null) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  },

  formatDate(iso) {
    if (!iso) return '-';
    try {
      return new Date(iso.replace(' ', 'T')).toLocaleString();
    } catch {
      return iso;
    }
  },

  renderTable(containerId, columns, rows, actionsHtml) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!rows || !rows.length) {
      el.innerHTML = '<p class="empty-state">No records found.</p>';
      return;
    }
    let html = '<div class="table-wrap"><table><thead><tr>';
    columns.forEach((c) => { html += `<th>${UI.esc(c.label)}</th>`; });
    if (actionsHtml) html += '<th>Actions</th>';
    html += '</tr></thead><tbody>';
    rows.forEach((row, i) => {
      html += '<tr>';
      columns.forEach((c) => {
        const val = c.render ? c.render(row) : row[c.key];
        html += `<td>${typeof val === 'string' ? val : UI.esc(val)}</td>`;
      });
      if (actionsHtml) html += `<td>${actionsHtml(row, i)}</td>`;
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
  },

  showPanel(panelId) {
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach((n) => n.classList.remove('active'));
    document.getElementById(panelId)?.classList.add('active');
    document.querySelector(`[data-panel="${panelId}"]`)?.classList.add('active');
  },

  toDatetimeLocal(iso) {
    if (!iso) return '';
    const d = new Date(iso.replace(' ', 'T'));
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  },
};
