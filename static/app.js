const commandEl = document.getElementById('command');
const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const clearBtn = document.getElementById('clear');
const openLogBtn = document.getElementById('openLog');
const errorEl = document.getElementById('error');
const healthEl = document.getElementById('health');
const jobsEl = document.getElementById('jobs');
const filesEl = document.getElementById('files');
const fileCount = document.getElementById('file-count');
const refreshFilesBtn = document.getElementById('refreshFiles');

const PHASES = {
  initialiseren: 'Initialiseren',
  parsing: 'Manifest lezen',
  downloading: 'Downloaden',
  decrypting: 'Decrypteren',
  muxing: 'Muxen',
  klaar: 'Klaar',
  gefaald: 'Gefaald',
  geannuleerd: 'Geannuleerd'
};

let activeJobId = null;

function phaseLabel(job) {
  if (!job) return '-';
  return PHASES[job.phase] || PHASES[job.status] || job.phase || job.status || '-';
}

function statusClass(job) {
  if (!job) return '';
  if (job.status === 'running') return job.phase === 'muxing' || job.phase === 'decrypting' ? 'warn' : 'active';
  if (job.status === 'done') return 'ok';
  if (job.status === 'failed') return 'err';
  return '';
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let value = bytes;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++; }
  return `${value.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function formatTime(seconds) {
  if (!seconds) return '-';
  return new Date(seconds * 1000).toLocaleString();
}

function showError(message) {
  errorEl.textContent = message || '';
}

async function api(path, options) {
  const response = await fetch(path, options);
  let data = null;
  try { data = await response.json(); } catch (e) { data = null; }
  if (!response.ok) throw new Error((data && data.error) || `HTTP ${response.status}`);
  return data;
}

function setActiveJob(job) {
  activeJobId = job ? job.id : null;
  openLogBtn.disabled = !job;
  stopBtn.disabled = !job;
  openLogBtn.dataset.job = job ? job.id : '';
}

function renderJobs(jobs) {
  jobsEl.innerHTML = '';
  if (!jobs.length) {
    jobsEl.innerHTML = '<li class="empty">Nog geen taken</li>';
    return;
  }
  for (const job of jobs) {
    const li = document.createElement('li');

    const top = document.createElement('div');
    top.className = 'job-top';
    const title = document.createElement('span');
    title.className = 'job-title';
    title.textContent = job.title || job.command;
    title.title = job.command;
    const phase = document.createElement('span');
    phase.className = `job-phase chip ${statusClass(job)}`;
    phase.textContent = phaseLabel(job);
    const pctTop = document.createElement('span');
    pctTop.className = `job-pct${job.progress == null ? '' : ' has-value'}`;
    pctTop.textContent = job.progress == null ? '—' : `${job.progress}%`;
    top.append(title, phase, pctTop);

    const meta = document.createElement('div');
    meta.className = 'job-meta';
    const time = document.createElement('span');
    time.textContent = formatTime(job.created);
    meta.append(time);
    if (job.detail) {
      const detail = document.createElement('span');
      detail.className = 'job-detail';
      detail.textContent = job.detail.length > 60 ? `${job.detail.slice(0, 60)}…` : job.detail;
      detail.title = job.detail;
      meta.append(detail);
    }
    const mini = document.createElement('span');
    mini.className = 'mini';
    const fill = document.createElement('i');
    fill.style.width = `${job.progress == null ? 0 : job.progress}%`;
    mini.append(fill);
    meta.append(mini);

    const actions = document.createElement('div');
    actions.className = 'job-actions';
    const logBtn = document.createElement('button');
    logBtn.className = 'btn tiny';
    logBtn.textContent = 'Log ↗';
    logBtn.onclick = () => window.open(`/log/${job.id}`, '_blank');
    actions.append(logBtn);
    if (job.status === 'running') {
      const stopJobBtn = document.createElement('button');
      stopJobBtn.className = 'btn tiny danger';
      stopJobBtn.textContent = 'Stop';
      stopJobBtn.onclick = async () => {
        try { await api(`/api/jobs/${job.id}/cancel`, { method: 'POST' }); await refreshJobs(); }
        catch (e) { showError(e.message); }
      };
      actions.append(stopJobBtn);
    }
    meta.append(actions);
    li.append(top, meta);
    jobsEl.append(li);
  }
}

function renderFiles(files) {
  filesEl.innerHTML = '';
  fileCount.textContent = files.length ? `(${files.length})` : '';
  if (!files.length) {
    filesEl.innerHTML = '<li class="empty">Nog geen bestanden</li>';
    return;
  }
  for (const file of files) {
    const li = document.createElement('li');
    const row = document.createElement('div');
    row.className = 'file-row';
    const name = document.createElement('a');
    name.className = 'name';
    const url = file.name.split('/').map(encodeURIComponent).join('/');
    name.href = `/api/files/${url}`;
    name.textContent = file.name;
    name.title = file.name;
    const size = document.createElement('span');
    size.className = 'size';
    size.textContent = formatBytes(file.size);
    const remove = document.createElement('button');
    remove.className = 'btn tiny danger';
    remove.textContent = 'Verwijder';
    remove.onclick = async () => {
      if (!confirm(`${file.name} verwijderen?`)) return;
      try { await api(`/api/files/${url}`, { method: 'DELETE' }); await refreshFiles(); }
      catch (e) { showError(e.message); }
    };
    row.append(name, size, remove);
    li.append(row);
    filesEl.append(li);
  }
}

async function refreshJobs() {
  try {
    const jobs = await api('/api/jobs');
    renderJobs(jobs);
    setActiveJob(jobs.find(job => job.status === 'running') || null);
  } catch (e) {
    showError(e.message);
  }
}

async function refreshFiles() {
  try { renderFiles(await api('/api/files')); }
  catch (e) { showError(e.message); }
}

startBtn.onclick = async () => {
  showError('');
  const command = commandEl.value.trim();
  if (!command) { showError('Plak eerst een commando'); return; }
  const isMobile = window.matchMedia('(max-width: 720px)').matches;
  const logWindow = isMobile ? null : window.open('about:blank', 'ndl-live-log');
  startBtn.disabled = true;
  try {
    const job = await api('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    if (logWindow) logWindow.location.href = `/log/${job.id}`;
    else if (!isMobile) showError('Log tab geblokkeerd door de browser; gebruik "Open live log".');
    await refreshJobs();
    if (isMobile) jobsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {
    if (logWindow) logWindow.close();
    showError(e.message);
  } finally {
    startBtn.disabled = false;
  }
};

stopBtn.onclick = async () => {
  if (!activeJobId) return;
  stopBtn.disabled = true;
  try { await api(`/api/jobs/${activeJobId}/cancel`, { method: 'POST' }); await refreshJobs(); }
  catch (e) { showError(e.message); }
};

clearBtn.onclick = async () => {
  try {
    await api('/api/jobs', { method: 'DELETE' });
    await refreshJobs();
  } catch (e) { showError(e.message); }
};

openLogBtn.onclick = () => {
  if (openLogBtn.dataset.job) window.open(`/log/${openLogBtn.dataset.job}`, '_blank');
};
refreshFilesBtn.onclick = refreshFiles;

api('/api/health')
  .then(data => {
    healthEl.textContent = data.ok ? 'verbonden' : 'serverfout';
    healthEl.className = `chip ${data.ok ? 'ok' : 'err'}`;
  })
  .catch(() => {
    healthEl.textContent = 'server onbereikbaar';
    healthEl.className = 'chip err';
  });

refreshJobs();
refreshFiles();
setInterval(refreshJobs, 2500);
setInterval(refreshFiles, 6000);
