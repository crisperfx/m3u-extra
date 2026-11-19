(function () {
  const GROUPS = [
    ['video', 'Video'],
    ['audio', 'Audio'],
    ['subtitle', 'Ondertiteling']
  ];

  function mainText(key, stream) {
    if (key === 'video') return stream.resolution || stream.name || 'Video';
    const language = stream.language || stream.name || 'Onbekend';
    return stream.language_code ? `${language} (${stream.language_code})` : language;
  }

  function extraText(key, stream) {
    const bits = [];
    if (stream.details) bits.push(stream.details);
    if (stream.track) bits.push(`spoor ${stream.track}`);
    return bits.join(' · ');
  }

  function build(job) {
    const streams = job && job.streams;
    if (!streams) return null;
    const rows = [];
    GROUPS.forEach(([key, label]) => {
      (streams[key] || []).forEach((stream) => rows.push({ key, label, stream }));
    });
    if (!rows.length) return null;

    const wrap = document.createElement('div');
    wrap.className = 'streams';
    const heading = document.createElement('div');
    heading.className = 'streams-head';
    heading.textContent = 'Geselecteerde streams';
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

  window.renderSelectedStreams = build;
})();
