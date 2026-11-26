const jobId = document.body.dataset.jobId;
const logEl = document.getElementById('log');
const logStatus = document.getElementById('log-status');
const phaseEl = document.getElementById('phase');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const jobTitle = document.getElementById('jobTitle');
const streamsEl = document.getElementById('jobStreams');
const progressEl = document.getElementById('jobProgress');
const autoscrollEl = document.getElementById('autoscroll');
const errorEl = document.getElementById('error');
const copyLog = document.getElementById('copyLog');
const topBtn = document.getElementById('backToTop');

const T = (key, vars) => (window.t ? window.t(key, vars) : key);
const TP = value => (window.tp ? window.tp(value) : value);
const TR = value => (window.tr ? window.tr(value) : value);

const ansiPattern = /\x1b\[[0-9;?]*[ -\/]*[@-~]/g;

let logText = '';
let progressLine = false;
let logStarted = false;
let lastJob = null;
let lastStatusKey = '';
let statusTimer = null;
let layoutTimer = null;

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

function followLog() {
  if (!autoscrollEl.checked) return;
  logEl.scrollTop = logEl.scrollHeight;
}

function refreshLayout() {
  document.body.classList.toggle('layout-refresh');
  void document.body.offsetHeight;
  document.body.classList.toggle('layout-refresh');
  void document.documentElement.offsetHeight;
}

function scheduleLayoutRefresh() {
  if (layoutTimer) clearTimeout(layoutTimer);
  layoutTimer = setTimeout(() => {
    layoutTimer = null;
    refreshLayout();
  }, 200);
}

function writeLog(text) {
  if (!logStarted) {
    logEl.textContent = '';
    logStarted = true;
  }
  const isProgress = text.endsWith('\r');
  const clean = text.replace(ansiPattern, '').replace(/\r$/, '');
  if (isProgress && progressLine) {
    const index = logText.lastIndexOf('\n');
    logText = logText.slice(0, index + 1) + clean;
  } else {
    if (progressLine) logText += '\n';
    logText += clean;
    if (!isProgress) logText += '\n';
    progressLine = isProgress;
  }
  logEl.textContent = logText;
  followLog();
  scheduleLayoutRefresh();
}

function statusKey(job) {
  return JSON.stringify([
    job.title,
    job.phase,
    job.status,
    job.progress,
    job.detail,
    job.streams,
    job.progress_streams,
    job.active_stream
  ]);
}

function updateStatus(job) {
  if (!job) return;
  const key = statusKey(job);
  if (key === lastStatusKey) return;
  lastStatusKey = key;
  streamsEl.replaceChildren();
  const streamBlock = window.renderSelectedStreams ? window.renderSelectedStreams(job) : null;
  if (streamBlock) streamsEl.append(streamBlock);
  progressEl.replaceChildren();
  const progressBlock = window.renderStreamProgress ? window.renderStreamProgress(job) : null;
  if (progressBlock) progressEl.append(progressBlock);
  phaseEl.textContent = phaseLabel(job);
  logStatus.textContent = phaseLabel(job);
  logStatus.className = `chip ${statusClass(job)}`;
  const value = job.progress == null ? 0 : job.progress;
  progressBar.style.width = `${value}%`;
  progressText.textContent = job.progress == null ? T('common.dash') : `${job.progress}%`;
}

function setJob(job) {
  if (!job) return;
  lastJob = job;
  updateStatus(job);
  const title = job.title || (job.command ? job.command.slice(0, 90) : T('log.jobFallback', { id: jobId }));
  if (jobTitle.textContent !== title) jobTitle.textContent = title;
}

async function refreshStatus() {
  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    if (!response.ok) return;
    setJob(await response.json());
  } catch (e) {
    errorEl.textContent = TR(e.message);
  }
}

const source = new EventSource(`/api/jobs/${jobId}/stream`);
source.onmessage = (event) => {
  try { writeLog(JSON.parse(event.data).line); }
  catch (e) { writeLog(`${event.data}\n`); }
};
source.addEventListener('status', (event) => {
  try { setJob(JSON.parse(event.data)); } catch (e) {}
});
source.addEventListener('end', (event) => {
  try { setJob(JSON.parse(event.data)); } catch (e) {}
  source.close();
  if (statusTimer) clearInterval(statusTimer);
  refreshStatus();
  refreshLayout();
});

copyLog.onclick = async () => {
  try {
    await navigator.clipboard.writeText(logText);
    copyLog.textContent = T('action.copied');
    setTimeout(() => { copyLog.textContent = T('action.copyLog'); }, 1200);
  } catch (e) {
    errorEl.textContent = TR(e.message);
  }
};

function updateTopButton() {
  topBtn.classList.toggle('visible', window.scrollY > 120);
}

window.addEventListener('scroll', updateTopButton, { passive: true });
topBtn.onclick = () => window.scrollTo(0, 0);
updateTopButton();

window.addEventListener('languagechange', () => {
  if (lastJob) setJob(lastJob);
  copyLog.textContent = T('action.copyLog');
});

window.addEventListener('load', refreshLayout);

refreshStatus();
statusTimer = setInterval(refreshStatus, 3000);
