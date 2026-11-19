(function () {
  const GROUPS = [
    ['video', 'stream.video'],
    ['audio', 'stream.audio'],
    ['subtitle', 'stream.subtitle']
  ];
  const T = key => (window.t ? window.t(key) : key);
  const TL = (label, code) => (window.tl ? window.tl(label, code) : label);

  function mainText(key, stream) {
    if (key === 'video') return stream.resolution || stream.name || T('stream.video');
    const raw = stream.language || stream.name || T('common.unknown');
    const language = TL(raw, stream.language_code);
    return stream.language_code ? `${language} (${stream.language_code})` : language;
  }

  function extraText(key, stream) {
    const bits = [];
    if (stream.details) bits.push(stream.details);
    if (stream.track) bits.push(`${T('stream.track')} ${stream.track}`);
    return bits.join(' · ');
  }

  function build(job) {
    const streams = job && job.streams;
    if (!streams) return null;
    const rows = [];
    GROUPS.forEach(([key, labelKey]) => {
      (streams[key] || []).forEach((stream) => rows.push({ key, label: T(labelKey), stream }));
    });
    if (!rows.length) return null;

    const wrap = document.createElement('div');
    wrap.className = 'streams';
    const heading = document.createElement('div');
    heading.className = 'streams-head';
    heading.textContent = T('stream.selected');
    wrap.append(heading);

    rows.forEach(({ key, label, stream }) => {
      const row = document.createElement('div');
      row.className = `stream-row ${key}`;
      if (stream.raw) row.title = stream.raw;

      const kind = document.createElement('span');
      kind.className = 'stream-kind';
      kind.textContent = label;

      const main = document.createElement('span');
      main.className = 'stream-main';
      main.textContent = mainText(key, stream);

      const extra = document.createElement('span');
      extra.className = 'stream-extra';
      extra.textContent = extraText(key, stream);

      row.append(kind, main, extra);
      wrap.append(row);
    });
    return wrap;
  }

  function progressText(item) {
    if (item.text) return item.text;
    const parts = [item.label, `${item.current}/${item.total}`, `${item.percent}%`, item.tail];
    return parts.filter(Boolean).join(' ');
  }

  function buildProgress(job) {
    const streams = job && job.progress_streams;
    if (!streams) return null;
    const rows = [];
    GROUPS.forEach(([key]) => {
      (streams[key] || []).forEach((item) => rows.push(item));
    });
    if (!rows.length) return null;

    const wrap = document.createElement('div');
    wrap.className = 'streams progress-streams';
    const heading = document.createElement('div');
    heading.className = 'streams-head';
    heading.textContent = T('stream.progress');
    wrap.append(heading);

    rows.forEach((item) => {
      const row = document.createElement('div');
      row.className = `stream-row progress-row ${item.kind}`;
      const top = document.createElement('div');
      top.className = 'progress-row-top';
      const text = document.createElement('span');
      text.className = 'progress-line';
      text.textContent = progressText(item);
      const pct = document.createElement('span');
      pct.className = 'stream-pct';
      pct.textContent = `${item.percent}%`;
      top.append(text, pct);
      const bar = document.createElement('div');
      bar.className = 'stream-bar';
      const fill = document.createElement('i');
      fill.style.width = `${Math.max(0, Math.min(100, item.percent || 0))}%`;
      bar.append(fill);
      row.append(top, bar);
      wrap.append(row);
    });
    return wrap;
  }

  function buildActive(job) {
    const item = job && job.active_stream;
    if (!item) return null;
    const wrap = document.createElement('div');
    wrap.className = 'streams active-stream';
    const heading = document.createElement('div');
    heading.className = 'streams-head';
    heading.textContent = T('stream.active');
    const row = document.createElement('div');
    row.className = `stream-row ${item.kind}`;
    const text = document.createElement('span');
    text.className = 'progress-line';
    text.textContent = progressText(item);
    const pct = document.createElement('span');
    pct.className = 'stream-pct';
    pct.textContent = `${item.percent}%`;
    row.append(text, pct);
    const bar = document.createElement('div');
    bar.className = 'active-bar';
    const fill = document.createElement('i');
    fill.style.width = `${Math.max(0, Math.min(100, item.percent || 0))}%`;
    bar.append(fill);
    wrap.append(heading, row, bar);
    return wrap;
  }

  window.renderSelectedStreams = build;
  window.renderStreamProgress = buildProgress;
  window.renderActiveStream = buildActive;
})();
