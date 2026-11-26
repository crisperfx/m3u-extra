const uploaderEl = document.getElementById('uploaderTag');
const resolutionEl = document.getElementById('resolutionTag');
const folderMoviesEl = document.getElementById('folderMovies');
const folderSeriesEl = document.getElementById('folderSeries');
const folderUploaderEl = document.getElementById('folderUploaderTag');
const folderResolutionEl = document.getElementById('folderResolutionTag');
const avoidDvVideoEl = document.getElementById('avoidDvVideo');
const autoStartEl = document.getElementById('autoStart');
const saveBtn = document.getElementById('saveOptions');
const errorEl = document.getElementById('error');
const savedEl = document.getElementById('saved');

const T = key => (window.t ? window.t(key) : key);
const TR = value => (window.tr ? window.tr(value) : value);

let savedTimer = null;

function showSaved() {
  savedEl.hidden = false;
  if (savedTimer) clearTimeout(savedTimer);
  savedTimer = setTimeout(() => { savedEl.hidden = true; }, 2000);
}

async function loadOptions() {
  try {
    const response = await fetch('/api/settings');
    const data = await response.json();
    uploaderEl.value = data.uploader_tag || '';
    resolutionEl.checked = data.resolution_tag !== false;
    folderMoviesEl.checked = data.folder_movies !== false;
    folderSeriesEl.checked = data.folder_series === true;
    folderUploaderEl.checked = data.folder_uploader_tag === true;
    folderResolutionEl.checked = data.folder_resolution_tag === true;
    avoidDvVideoEl.checked = data.avoid_dv_video !== false;
    autoStartEl.checked = data.auto_start !== false;
    savedEl.hidden = true;
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

saveBtn.onclick = async () => {
  errorEl.textContent = '';
  saveBtn.disabled = true;
  try {
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uploader_tag: uploaderEl.value,
        resolution_tag: resolutionEl.checked,
        folder_movies: folderMoviesEl.checked,
        folder_series: folderSeriesEl.checked,
        folder_uploader_tag: folderUploaderEl.checked,
        folder_resolution_tag: folderResolutionEl.checked,
        avoid_dv_video: avoidDvVideoEl.checked,
        auto_start: autoStartEl.checked
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    uploaderEl.value = data.uploader_tag || '';
    showSaved();
  } catch (e) {
    errorEl.textContent = TR(e.message);
  } finally {
    saveBtn.disabled = false;
  }
};

window.addEventListener('languagechange', () => {
  savedEl.textContent = T('options.saved');
});

loadOptions();
