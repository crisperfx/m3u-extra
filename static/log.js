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

const ansiPattern = /\x1b\[[0-9;?]*[ -\/]*[@-~]/g;

let logText = '';
let progressLine = false;
let logStarted = false;

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
  if (autoscrollEl.checked) logEl.scrollTop = logEl.scrollHeight;
}

function updateStatus(job) {
  if (!job) return;
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
  progressText.textContent = job.progress == null ? '—' : `${job.progress}%`;
}

async function refreshStatus() {
  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    if (!response.ok) return;
    const job = await response.json();
    updateStatus(job);
    jobTitle.textContent = job.title || (job.command ? job.command.slice(0, 90) : `Taak ${jobId}`);
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

const source = new EventSource(`/api/jobs/${jobId}/stream`);
source.onmessage = (event) => {
  try { writeLog(JSON.parse(event.data).line); }
  catch (e) { writeLog(`${event.data}\n`); }
};
source.addEventListener('status', (event) => {
  try { updateStatus(JSON.parse(event.data)); } catch (e) {}
});
source.addEventListener('end', (event) => {
  try { updateStatus(JSON.parse(event.data)); } catch (e) {}
  source.close();
  refreshStatus();
});

copyLog.onclick = async () => {
  try {
    await navigator.clipboard.writeText(logText);
    copyLog.textContent = 'gekopieerd';
    setTimeout(() => { copyLog.textContent = 'Kopieer log'; }, 1200);
  } catch (e) {
    errorEl.textContent = e.message;
  }
};

refreshStatus();
setInterval(refreshStatus, 3000);
