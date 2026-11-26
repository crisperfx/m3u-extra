const commandEl = document.getElementById('command');
const startBtn = document.getElementById('start');
const queueBtn = document.getElementById('queueJob');
const startQueueBtn = document.getElementById('startQueue');
const stopBtn = document.getElementById('stop');
const clearBtn = document.getElementById('clear');
const openLogBtn = document.getElementById('openLog');
const errorEl = document.getElementById('error');
const healthEl = document.getElementById('health');
const jobsEl = document.getElementById('jobs');
const queueEl = document.getElementById('queue');
const queuePanel = document.getElementById('queuePanel');
const queueCount = document.getElementById('queue-count');
const filesEl = document.getElementById('files');
const fileCount = document.getElementById('file-count');
const refreshFilesBtn = document.getElementById('refreshFiles');

const T = (key, vars) => (window.t ? window.t(key, vars) : key);
const TP = value => (window.tp ? window.tp(value) : value);
const TR = value => (window.tr ? window.tr(value) : value);

let activeJobId = null;
let lastJobs = [];
let editingJobId = null;
const queueDrafts = {};
const collapsedJobs = new Set();
const jobStatuses = new Map();
let healthOk = null;
let healthKey = 'health.connecting';

function phaseLabel(job) {
  if (!job) return T('common.dash');
  const raw = job.phase || job.status;
  return raw ? TP(raw) : T('common.dash');
}

function statusClass(job) {
  if (!job) return '';
  if (job.status === 'queued' || job.status === 'needs_selection') return 'warn';
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
  errorEl.textContent = TR(message) || '';
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
    jobsEl.innerHTML = `<li class="empty">${T('empty.noJobs')}</li>`;
    return;
  }
  for (const job of jobs) {
    const li = document.createElement('li');
    li.className = 'job';

    const top = document.createElement('div');
    top.className = 'job-top';
    if (!jobStatuses.has(job.id)) {
      if (job.status !== 'running') collapsedJobs.add(job.id);
      jobStatuses.set(job.id, job.status);
    } else if (job.status === 'running' && jobStatuses.get(job.id) !== 'running') {
      collapsedJobs.delete(job.id);
      jobStatuses.set(job.id, job.status);
    } else if (job.status !== jobStatuses.get(job.id)) {
      jobStatuses.set(job.id, job.status);
    }
    const collapsed = collapsedJobs.has(job.id);
    const toggle = document.createElement('button');
    toggle.className = 'job-toggle';
    toggle.textContent = collapsed ? '▸' : '▾';
    toggle.title = T('action.toggleDetails');
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.onclick = () => {
      if (collapsed) collapsedJobs.delete(job.id); else collapsedJobs.add(job.id);
      renderJobs(lastJobs);
    };
    const title = document.createElement('span');
    title.className = 'job-title';
    title.textContent = job.title || job.command;
    title.title = job.command;
    const phase = document.createElement('span');
    phase.className = `job-phase chip ${statusClass(job)}`;
    phase.textContent = phaseLabel(job);
    const pctTop = document.createElement('span');
    pctTop.className = `job-pct${job.progress == null ? '' : ' has-value'}`;
    pctTop.textContent = job.progress == null ? T('common.dash') : `${job.progress}%`;
    top.append(toggle, title, phase, pctTop);

    const details = document.createElement('div');
    details.className = 'job-details';
    details.hidden = collapsed;
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
    if (job.status !== 'queued') {
      const logBtn = document.createElement('button');
      logBtn.className = 'btn tiny';
      logBtn.textContent = T('action.log');
      logBtn.onclick = () => window.open(`/log/${job.id}`, '_blank');
      actions.append(logBtn);
    }
    if (job.status === 'running' || job.status === 'queued') {
      const stopJobBtn = document.createElement('button');
      stopJobBtn.className = 'btn tiny danger';
      stopJobBtn.textContent = T('action.stop');
      stopJobBtn.onclick = async () => {
        try { await api(`/api/jobs/${job.id}/cancel`, { method: 'POST' }); await refreshJobs(); }
        catch (e) { showError(e.message); }
      };
      actions.append(stopJobBtn);
    }
    if (job.status === 'failed' && !job.archived) {
      const retryBtn = document.createElement('button');
      retryBtn.className = 'btn tiny';
      retryBtn.textContent = T('action.retry');
      retryBtn.onclick = async () => {
        retryBtn.disabled = true;
        try {
          await api(`/api/jobs/${job.id}/retry`, { method: 'POST' });
          await refreshJobs();
        } catch (e) {
          showError(e.message);
          retryBtn.disabled = false;
        }
      };
      actions.append(retryBtn);
    }
    meta.append(actions);
    details.append(meta);
    const streamBlock = window.renderSelectedStreams ? window.renderSelectedStreams(job) : null;
    if (streamBlock) details.append(streamBlock);
    const activeBlock = window.renderActiveStream ? window.renderActiveStream(job) : null;
    if (activeBlock) details.append(activeBlock);
    li.append(top, details);
    jobsEl.append(li);
  }
}

const QUEUE_FIELDS = [
  ['video', 'stream.video'],
  ['audio', 'stream.audio'],
  ['subtitle', 'stream.subtitle']
];

function streamDisplay(kind, stream) {
  const main = kind === 'video'
    ? (stream.resolution || stream.name || T('stream.video'))
    : ((stream.language ? `${stream.language}${stream.language_code ? ` (${stream.language_code})` : ''}` : stream.name) || T('common.unknown'));
  const bits = [];
  if (stream.details) bits.push(stream.details);
  if (stream.track) bits.push(`${T('stream.track')} ${stream.track}`);
  return bits.length ? `${main} · ${bits.join(' · ')}` : main;
}

function initialTracks(job) {
  const result = {};
  for (const [kind] of QUEUE_FIELDS) {
    const items = ((job.streams || {})[kind] || []).filter(item => item.track != null);
    if (!items.length) continue;
    const selector = (job.selectors || {})[kind] || '';
    const match = selector.match(/id=\^\(([^)]+)\)\$/);
    if (match) {
      const ids = match[1].split('|').map(value => value.replace(/\\/g, ''));
      result[kind] = items.filter(item => ids.includes(String(item.track))).map(item => String(item.track));
    } else {
      result[kind] = items.map(item => String(item.track));
    }
  }
  return result;
}

function buildQueueEditor(job) {
  const wrap = document.createElement('div');
  wrap.className = 'queue-editor';
  const heading = document.createElement('div');
  heading.className = 'queue-editor-title';
  heading.textContent = T('edit.title');
  wrap.append(heading);
  if (job.status === 'needs_selection') {
    const probeHint = document.createElement('div');
    probeHint.className = 'edit-hint';
    probeHint.textContent = T('edit.probeHint');
    wrap.append(probeHint);
  }

  const hasTracks = QUEUE_FIELDS.some(([kind]) =>
    ((job.streams || {})[kind] || []).some(item => item.track != null));
  const draft = queueDrafts[job.id] || (hasTracks
    ? { mode: 'tracks', tracks: initialTracks(job) }
    : { mode: 'selector', ...(job.selectors || {}) });
  queueDrafts[job.id] = draft;

  if (draft.mode === 'tracks' && hasTracks) {
    const hint = document.createElement('div');
    hint.className = 'edit-hint';
    hint.textContent = T('edit.hint');
    wrap.append(hint);
    for (const [kind, labelKey] of QUEUE_FIELDS) {
      const items = ((job.streams || {})[kind] || []).filter(item => item.track != null);
      if (!items.length) continue;
      if (!draft.tracks) draft.tracks = {};
      if (!Array.isArray(draft.tracks[kind])) draft.tracks[kind] = initialTracks(job)[kind] || [];
      const group = document.createElement('div');
      group.className = 'track-group';
      const label = document.createElement('div');
      label.className = 'track-group-title';
      label.textContent = T(labelKey);
      group.append(label);
      for (const item of items) {
        const id = String(item.track);
        const row = document.createElement('label');
        row.className = 'track-row';
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.checked = draft.tracks[kind].includes(id);
        box.onchange = () => {
          const values = new Set(draft.tracks[kind]);
          if (box.checked) values.add(id); else values.delete(id);
          draft.tracks[kind] = [...values];
          queueDrafts[job.id] = draft;
        };
        const text = document.createElement('span');
        text.textContent = streamDisplay(kind, item);
        row.append(box, text);
        group.append(row);
      }
      wrap.append(group);
    }
  } else {
    draft.mode = 'selector';
    const fields = document.createElement('div');
    fields.className = 'queue-fields';
    for (const [key, labelKey] of QUEUE_FIELDS) {
      const field = document.createElement('label');
      field.className = 'queue-field';
      const label = document.createElement('span');
      label.textContent = T(labelKey);
      const input = document.createElement('input');
      input.type = 'text';
      input.value = draft[key] || '';
      input.placeholder = T('edit.placeholder');
      input.oninput = () => {
        draft[key] = input.value;
        queueDrafts[job.id] = draft;
      };
      field.append(label, input);
      fields.append(field);
    }
    wrap.append(fields);
  }

  const actions = document.createElement('div');
  actions.className = 'queue-actions';
  const saveBtn = document.createElement('button');
  saveBtn.className = 'btn tiny primary';
  saveBtn.textContent = T('action.save');
  saveBtn.onclick = async () => {
    saveBtn.disabled = true;
    const payload = draft.mode === 'tracks'
      ? {
          tracks: Object.fromEntries(QUEUE_FIELDS
            .filter(([kind]) => Array.isArray((draft.tracks || {})[kind]))
            .map(([kind]) => [kind, draft.tracks[kind]]))
        }
      : Object.fromEntries(QUEUE_FIELDS.map(([kind]) => [kind, draft[kind] || '']));
    try {
      await api(`/api/jobs/${job.id}/streams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      delete queueDrafts[job.id];
      editingJobId = null;
      await refreshJobs();
    } catch (e) {
      showError(e.message);
      saveBtn.disabled = false;
    }
  };
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn tiny subtle';
  cancelBtn.textContent = T('action.cancel');
  cancelBtn.onclick = () => {
    delete queueDrafts[job.id];
    editingJobId = null;
    renderQueue(lastJobs);
  };
  actions.append(saveBtn, cancelBtn);
  wrap.append(actions);
  return wrap;
}

function renderQueue(jobs) {
  const waiting = jobs.filter(job => job.status === 'queued' || job.status === 'needs_selection');
  queuePanel.hidden = waiting.length === 0;
  queueCount.textContent = waiting.length ? `(${waiting.length})` : '';
  queueEl.innerHTML = '';
  for (const job of waiting) {
    const li = document.createElement('li');
    li.className = 'queue-item';
    const row = document.createElement('div');
    row.className = 'queue-row';
    const title = document.createElement('span');
    title.className = 'queue-title';
    title.textContent = job.title || job.command;
    title.title = job.command;
    const phase = document.createElement('span');
    phase.className = `job-phase chip ${statusClass(job)}`;
    phase.textContent = phaseLabel(job);
    const editBtn = document.createElement('button');
    editBtn.className = 'btn tiny subtle';
    editBtn.textContent = T('action.editStreams');
    editBtn.onclick = () => {
      editingJobId = editingJobId === job.id ? null : job.id;
      renderQueue(lastJobs);
    };
    row.append(title, phase, editBtn);
    li.append(row);
    if (editingJobId === job.id) li.append(buildQueueEditor(job));
    queueEl.append(li);
  }
}

function renderFiles(files) {
  filesEl.innerHTML = '';
  fileCount.textContent = files.length ? `(${files.length})` : '';
  if (!files.length) {
    filesEl.innerHTML = `<li class="empty">${T('empty.noFiles')}</li>`;
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
    remove.textContent = T('action.delete');
    remove.onclick = async () => {
      if (!confirm(T('confirm.deleteFile', { name: file.name }))) return;
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
    lastJobs = jobs;
    renderJobs(jobs);
    if (!editingJobId) renderQueue(jobs);
    setActiveJob(jobs.find(job => job.status === 'running') || null);
  } catch (e) {
    showError(e.message);
  }
}

async function refreshFiles() {
  try { renderFiles(await api('/api/files')); }
  catch (e) { showError(e.message); }
}

async function submitJob(queue) {
  showError('');
  const command = commandEl.value.trim();
  if (!command) { showError(T('error.pasteCommand')); return; }
  const isMobile = window.matchMedia('(max-width: 720px)').matches;
  startBtn.disabled = true;
  queueBtn.disabled = true;
  try {
    await api('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, queue })
    });
    await refreshJobs();
    if (isMobile) jobsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {
    showError(e.message);
  } finally {
    startBtn.disabled = false;
    queueBtn.disabled = false;
  }
}

startBtn.onclick = () => submitJob(false);
queueBtn.onclick = () => submitJob(true);

startQueueBtn.onclick = async () => {
  startQueueBtn.disabled = true;
  try {
    await api('/api/jobs/queue/start', { method: 'POST' });
    await refreshJobs();
  } catch (e) {
    showError(e.message);
  } finally {
    startQueueBtn.disabled = false;
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

function renderHealth() {
  healthEl.textContent = T(healthKey);
  healthEl.className = `chip ${healthOk ? 'ok' : 'err'}`;
}

api('/api/health')
  .then(data => {
    healthOk = data.ok;
    healthKey = data.ok ? 'health.connected' : 'health.error';
    renderHealth();
  })
  .catch(() => {
    healthOk = false;
    healthKey = 'health.unreachable';
    renderHealth();
  });

window.addEventListener('languagechange', () => {
  if (healthOk !== null) renderHealth();
  refreshJobs();
  refreshFiles();
});

refreshJobs();
refreshFiles();
setInterval(refreshJobs, 2500);
setInterval(refreshFiles, 6000);
