(function () {
  const STORAGE_KEY = 'ndl-language';
  const DEFAULT_LANGUAGE = 'nl';

  const translations = {
    nl: {
      'app.title': 'Crisperfx Stream Studio',
      'log.title': 'Log · Crisperfx Stream Studio',
      'brand.subtitle': 'N_m3u8DL-RE besturing',
      'log.subtitle': 'Live log',
      'language.label': 'Taal',
      'health.connecting': 'verbinden...',
      'health.connected': 'verbonden',
      'health.error': 'serverfout',
      'health.unreachable': 'server onbereikbaar',
      'panel.newTask': 'Nieuwe taak',
      'panel.command': 'Commando',
      'panel.overview': 'Overzicht',
      'panel.tasks': 'Taken',
      'panel.storage': 'Opslag',
      'panel.files': 'Bestanden',
      'command.placeholder': 'N_m3u8DL-RE.exe "https://.../index.mpd" --save-name "Naam" -H "Referer: https://..." --key KID:KEY -M format=mkv',
      'action.start': 'Start download',
      'action.openLog': 'Open live log ↗',
      'action.stop': 'Stop',
      'action.log': 'Log ↗',
      'action.delete': 'Verwijder',
      'action.clearHistory': 'Geschiedenis + logs wissen',
      'action.refresh': 'Vernieuwen',
      'action.back': '← Terug naar GUI',
      'action.copyLog': 'Kopieer log',
      'action.copied': 'gekopieerd',
      'action.top': '↑ Boven',
      'action.options': 'Opties',
      'action.queue': 'In wachtrij',
      'action.startQueue': 'Wachtrij starten',
      'action.save': 'Opslaan',
      'action.editStreams': 'Streams wijzigen',
      'action.retry': 'Opnieuw proberen',
      'action.cancel': 'Annuleren',
      'action.toggleDetails': 'Details tonen/verbergen',
      'edit.title': 'Geselecteerde streams',
      'edit.placeholder': 'bijv. lang=nld of leeg voor geen',
      'edit.hint': 'Vink stream(s) aan. Niets aanvinken = alle streams van dat type (for=all).',
      'edit.probeHint': 'De streams zijn gevonden. Na opslaan start de taak met de aangevinkte streams.',
      'panel.queue': 'Wachtrij',
      'panel.queueHint': 'Wachtend',
      'options.title': 'Opties',
      'options.subtitle': 'Instellingen',
      'options.groupNames': 'Namen',
      'options.uploader': 'Uploader-tag',
      'options.uploaderPlaceholder': 'bijv. YTS',
      'options.uploaderHelp': 'Komt achter de titel, bijvoorbeeld: The Odyssey (2026) 1080p YTS',
      'options.resolution': 'Resolutie automatisch toevoegen',
      'options.autoStart': 'Downloads direct starten',
      'options.autoStartHelp': 'Uit: nieuwe downloads gaan naar de wachtrij en starten pas via Wachtrij starten.',
      'options.saved': 'Opgeslagen',
      'phase.queued': 'In wachtrij',
      'phase.needsSelection': 'Kies streams',
      'hint.title': 'Hoe werkt dit?',
      'hint.body': 'Plak het volledige commando. <code>N_m3u8DL-RE.exe</code> wordt automatisch door de Linux-versie vervangen. Bestanden komen in <code>/downloads/&lt;titel&gt;/</code> terecht. Gebruik <strong>Log ↗</strong> om het live logboek te openen; taken die via de extensie starten verschijnen hier vanzelf.',
      'empty.noJobs': 'Nog geen taken',
      'empty.noFiles': 'Nog geen bestanden',
      'common.dash': '—',
      'common.none': 'geen',
      'common.unknown': 'onbekend',
      'stream.video': 'Video',
      'stream.audio': 'Audio',
      'stream.subtitle': 'Ondertiteling',
      'stream.track': 'spoor',
      'language.nld': 'Nederlands',
      'language.eng': 'Engels',
      'language.fra': 'Frans',
      'language.deu': 'Duits',
      'language.spa': 'Spaans',
      'language.ita': 'Italiaans',
      'language.por': 'Portugees',
      'language.jpn': 'Japans',
      'language.kor': 'Koreaans',
      'language.zho': 'Chinees',
      'language.rus': 'Russisch',
      'language.ara': 'Arabisch',
      'language.hin': 'Hindi',
      'stream.selected': 'Geselecteerde streams:',
      'stream.progress': 'Voortgang per stream:',
      'stream.active': 'Actieve stream:',
      'phase.initialiseren': 'Initialiseren',
      'phase.parsing': 'Manifest lezen',
      'phase.downloading': 'Downloaden',
      'phase.decrypting': 'Decrypteren',
      'phase.muxing': 'Muxen',
      'phase.klaar': 'Klaar',
      'phase.gefaald': 'Gefaald',
      'phase.geannuleerd': 'Geannuleerd',
      'phase.running': 'Actief',
      'log.loadingTask': 'Taak laden...',
      'log.jobFallback': 'Taak {id}',
      'log.loadingLog': 'Log laden...',
      'log.liveLog': 'Live log',
      'log.follow': 'Log volgen',
      'log.status': 'inactief',
      'error.pasteCommand': 'Plak eerst een commando',
      'error.commandTooLong': 'Commando is te lang',
      'error.invalidCommand': 'Ongeldig commando',
      'error.invalidCharacter': 'Ongeldig teken in commando',
      'error.commandPrefix': 'Commando moet beginnen met N_m3u8DL-RE of N_m3u8DL-RE.exe',
      'error.saveDir': '--save-dir moet binnen /downloads blijven',
      'error.maxConcurrent': 'Maximaal {count} gelijktijdige taken',
      'error.invalidToken': 'Ongeldige token',
      'error.jobDone': 'Taak is al klaar',
      'confirm.deleteFile': '{name} verwijderen?'
    },
    en: {
      'app.title': 'Crisperfx Stream Studio',
      'log.title': 'Log · Crisperfx Stream Studio',
      'brand.subtitle': 'N_m3u8DL-RE controller',
      'log.subtitle': 'Live log',
      'language.label': 'Language',
      'health.connecting': 'connecting...',
      'health.connected': 'connected',
      'health.error': 'server error',
      'health.unreachable': 'server unreachable',
      'panel.newTask': 'New job',
      'panel.command': 'Command',
      'panel.overview': 'Overview',
      'panel.tasks': 'Jobs',
      'panel.storage': 'Storage',
      'panel.files': 'Files',
      'command.placeholder': 'N_m3u8DL-RE.exe "https://.../index.mpd" --save-name "Name" -H "Referer: https://..." --key KID:KEY -M format=mkv',
      'action.start': 'Start download',
      'action.openLog': 'Open live log ↗',
      'action.stop': 'Stop',
      'action.log': 'Log ↗',
      'action.delete': 'Delete',
      'action.clearHistory': 'Clear history + logs',
      'action.refresh': 'Refresh',
      'action.back': '← Back to GUI',
      'action.copyLog': 'Copy log',
      'action.copied': 'copied',
      'action.top': '↑ Top',
      'action.options': 'Options',
      'action.queue': 'Queue',
      'action.startQueue': 'Start queue',
      'action.save': 'Save',
      'action.editStreams': 'Edit streams',
      'action.retry': 'Retry',
      'action.cancel': 'Cancel',
      'action.toggleDetails': 'Show/hide details',
      'edit.title': 'Selected streams',
      'edit.placeholder': 'e.g. lang=nld or empty for none',
      'edit.hint': 'Check streams. Checking none = all streams of that type (for=all).',
      'edit.probeHint': 'Streams are ready. Saving starts the job with the checked streams.',
      'panel.queue': 'Queue',
      'panel.queueHint': 'Waiting',
      'options.title': 'Options',
      'options.subtitle': 'Settings',
      'options.groupNames': 'Names',
      'options.uploader': 'Uploader tag',
      'options.uploaderPlaceholder': 'e.g. YTS',
      'options.uploaderHelp': 'Appended to the title, for example: The Odyssey (2026) 1080p YTS',
      'options.resolution': 'Add resolution automatically',
      'options.autoStart': 'Start downloads immediately',
      'options.autoStartHelp': 'Off: new downloads go to the queue and only start via Start queue.',
      'options.saved': 'Saved',
      'phase.queued': 'Queued',
      'phase.needsSelection': 'Choose streams',
      'hint.title': 'How does this work?',
      'hint.body': 'Paste the full command. <code>N_m3u8DL-RE.exe</code> is automatically replaced by the Linux binary. Files are stored in <code>/downloads/&lt;title&gt;/</code>. Use <strong>Log ↗</strong> to open the live log; jobs started by the extension appear here automatically.',
      'empty.noJobs': 'No jobs yet',
      'empty.noFiles': 'No files yet',
      'common.dash': '—',
      'common.none': 'none',
      'common.unknown': 'unknown',
      'stream.video': 'Video',
      'stream.audio': 'Audio',
      'stream.subtitle': 'Subtitles',
      'stream.track': 'track',
      'language.nld': 'Dutch',
      'language.eng': 'English',
      'language.fra': 'French',
      'language.deu': 'German',
      'language.spa': 'Spanish',
      'language.ita': 'Italian',
      'language.por': 'Portuguese',
      'language.jpn': 'Japanese',
      'language.kor': 'Korean',
      'language.zho': 'Chinese',
      'language.rus': 'Russian',
      'language.ara': 'Arabic',
      'language.hin': 'Hindi',
      'stream.selected': 'Selected streams:',
      'stream.progress': 'Progress per stream:',
      'stream.active': 'Active stream:',
      'phase.initialiseren': 'Initializing',
      'phase.parsing': 'Reading manifest',
      'phase.downloading': 'Downloading',
      'phase.decrypting': 'Decrypting',
      'phase.muxing': 'Muxing',
      'phase.klaar': 'Done',
      'phase.gefaald': 'Failed',
      'phase.geannuleerd': 'Cancelled',
      'phase.running': 'Active',
      'log.loadingTask': 'Loading job...',
      'log.jobFallback': 'Job {id}',
      'log.loadingLog': 'Loading log...',
      'log.liveLog': 'Live log',
      'log.follow': 'Follow log',
      'log.status': 'inactive',
      'error.pasteCommand': 'Paste a command first',
      'error.commandTooLong': 'Command is too long',
      'error.invalidCommand': 'Invalid command',
      'error.invalidCharacter': 'Invalid character in command',
      'error.commandPrefix': 'Command must start with N_m3u8DL-RE or N_m3u8DL-RE.exe',
      'error.saveDir': '--save-dir must stay inside /downloads',
      'error.maxConcurrent': 'At most {count} concurrent jobs',
      'error.invalidToken': 'Invalid token',
      'error.jobDone': 'Job is already finished',
      'confirm.deleteFile': 'Delete {name}?'
    },
    fr: {
      'app.title': 'Crisperfx Stream Studio',
      'log.title': 'Journal · Crisperfx Stream Studio',
      'brand.subtitle': 'Contrôleur N_m3u8DL-RE',
      'log.subtitle': 'Journal en direct',
      'language.label': 'Langue',
      'health.connecting': 'connexion...',
      'health.connected': 'connecté',
      'health.error': 'erreur serveur',
      'health.unreachable': 'serveur inaccessible',
      'panel.newTask': 'Nouvelle tâche',
      'panel.command': 'Commande',
      'panel.overview': 'Aperçu',
      'panel.tasks': 'Tâches',
      'panel.storage': 'Stockage',
      'panel.files': 'Fichiers',
      'command.placeholder': 'N_m3u8DL-RE.exe "https://.../index.mpd" --save-name "Nom" -H "Referer: https://..." --key KID:KEY -M format=mkv',
      'action.start': 'Démarrer le téléchargement',
      'action.openLog': 'Ouvrir le journal en direct ↗',
      'action.stop': 'Arrêter',
      'action.log': 'Journal ↗',
      'action.delete': 'Supprimer',
      'action.clearHistory': 'Effacer l’historique + les journaux',
      'action.refresh': 'Actualiser',
      'action.back': '← Retour à l’interface',
      'action.copyLog': 'Copier le journal',
      'action.copied': 'copié',
      'action.top': '↑ Haut',
      'action.options': 'Options',
      'action.queue': 'File d’attente',
      'action.startQueue': 'Démarrer la file',
      'action.save': 'Enregistrer',
      'action.editStreams': 'Modifier les flux',
      'action.retry': 'Réessayer',
      'action.cancel': 'Annuler',
      'action.toggleDetails': 'Afficher/masquer les détails',
      'edit.title': 'Flux sélectionnés',
      'edit.placeholder': 'ex. lang=fra ou vide pour aucun',
      'edit.hint': 'Cochez les flux. Aucune case cochée = tous les flux de ce type (for=all).',
      'edit.probeHint': 'Les flux sont prêts. L’enregistrement lance la tâche avec les flux cochés.',
      'panel.queue': 'File d’attente',
      'panel.queueHint': 'En attente',
      'options.title': 'Options',
      'options.subtitle': 'Paramètres',
      'options.groupNames': 'Noms',
      'options.uploader': 'Tag de téléverseur',
      'options.uploaderPlaceholder': 'ex. YTS',
      'options.uploaderHelp': 'Ajouté après le titre, par exemple : The Odyssey (2026) 1080p YTS',
      'options.resolution': 'Ajouter la résolution automatiquement',
      'options.autoStart': 'Démarrer les téléchargements immédiatement',
      'options.autoStartHelp': 'Désactivé : les nouveaux téléchargements vont dans la file et démarrent seulement via Démarrer la file.',
      'options.saved': 'Enregistré',
      'phase.queued': 'En file d’attente',
      'phase.needsSelection': 'Choisir les flux',
      'hint.title': 'Comment ça marche ?',
      'hint.body': 'Collez la commande complète. <code>N_m3u8DL-RE.exe</code> est automatiquement remplacé par la version Linux. Les fichiers sont enregistrés dans <code>/downloads/&lt;titre&gt;/</code>. Utilisez <strong>Journal ↗</strong> pour ouvrir le journal en direct ; les tâches lancées par l’extension apparaissent ici automatiquement.',
      'empty.noJobs': 'Aucune tâche',
      'empty.noFiles': 'Aucun fichier',
      'common.dash': '—',
      'common.none': 'aucun',
      'common.unknown': 'inconnu',
      'stream.video': 'Vidéo',
      'stream.audio': 'Audio',
      'stream.subtitle': 'Sous-titres',
      'stream.track': 'piste',
      'language.nld': 'Néerlandais',
      'language.eng': 'Anglais',
      'language.fra': 'Français',
      'language.deu': 'Allemand',
      'language.spa': 'Espagnol',
      'language.ita': 'Italien',
      'language.por': 'Portugais',
      'language.jpn': 'Japonais',
      'language.kor': 'Coréen',
      'language.zho': 'Chinois',
      'language.rus': 'Russe',
      'language.ara': 'Arabe',
      'language.hin': 'Hindi',
      'stream.selected': 'Flux sélectionnés :',
      'stream.progress': 'Progression par flux :',
      'stream.active': 'Flux actif :',
      'phase.initialiseren': 'Initialisation',
      'phase.parsing': 'Lecture du manifeste',
      'phase.downloading': 'Téléchargement',
      'phase.decrypting': 'Déchiffrement',
      'phase.muxing': 'Muxage',
      'phase.klaar': 'Terminé',
      'phase.gefaald': 'Échec',
      'phase.geannuleerd': 'Annulé',
      'phase.running': 'Actif',
      'log.loadingTask': 'Chargement de la tâche...',
      'log.jobFallback': 'Tâche {id}',
      'log.loadingLog': 'Chargement du journal...',
      'log.liveLog': 'Journal en direct',
      'log.follow': 'Suivre le journal',
      'log.status': 'inactif',
      'error.pasteCommand': 'Collez d’abord une commande',
      'error.commandTooLong': 'Commande trop longue',
      'error.invalidCommand': 'Commande invalide',
      'error.invalidCharacter': 'Caractère invalide dans la commande',
      'error.commandPrefix': 'La commande doit commencer par N_m3u8DL-RE ou N_m3u8DL-RE.exe',
      'error.saveDir': '--save-dir doit rester dans /downloads',
      'error.maxConcurrent': 'Au maximum {count} tâches simultanées',
      'error.invalidToken': 'Jeton invalide',
      'error.jobDone': 'La tâche est déjà terminée',
      'confirm.deleteFile': 'Supprimer {name} ?'
    }
  };

  const LANGUAGE_ORDER = ['nl', 'en', 'fr'];
  const LANGUAGE_TITLE_KEYS = { nl: 'language.nld', en: 'language.eng', fr: 'language.fra' };

  const LANGUAGE_CODES = {
    nederlands: 'nld', nld: 'nld', dut: 'nld', nl: 'nld',
    engels: 'eng', english: 'eng', eng: 'eng', en: 'eng',
    frans: 'fra', fra: 'fra', fre: 'fra', fr: 'fra',
    duits: 'deu', deu: 'deu', ger: 'deu', de: 'deu',
    spaans: 'spa', spa: 'spa', es: 'spa',
    italiaans: 'ita', ita: 'ita', it: 'ita',
    portugees: 'por', por: 'por', pt: 'por',
    japans: 'jpn', jpn: 'jpn', ja: 'jpn',
    koreaans: 'kor', kor: 'kor', ko: 'kor',
    chinees: 'zho', zho: 'zho', chi: 'zho', zh: 'zho',
    russisch: 'rus', rus: 'rus', ru: 'rus',
    arabisch: 'ara', ara: 'ara', ar: 'ara',
    hindi: 'hin', hin: 'hin', hi: 'hin'
  };

  const serverMessages = [
    [/^Plak eerst een commando$/, 'error.pasteCommand'],
    [/^Commando is te lang$/, 'error.commandTooLong'],
    [/^Ongeldig commando$/, 'error.invalidCommand'],
    [/^Ongeldig teken in commando$/, 'error.invalidCharacter'],
    [/^Commando moet beginnen met N_m3u8DL-RE of N_m3u8DL-RE\.exe$/, 'error.commandPrefix'],
    [/^--save-dir moet binnen \/downloads blijven$/, 'error.saveDir'],
    [/^Maximaal (\d+) gelijktijdige taken$/, 'error.maxConcurrent', match => ({ count: match[1] })],
    [/^Ongeldige token$/, 'error.invalidToken'],
    [/^Taak is al klaar$/, 'error.jobDone']
  ];

  function readStoredLanguage() {
    try { return window.localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  let language = translations[readStoredLanguage()] ? readStoredLanguage() : DEFAULT_LANGUAGE;

  function t(key, vars) {
    let text = (translations[language] && translations[language][key]) || translations.nl[key] || key;
    if (vars) {
      Object.keys(vars).forEach(name => {
        text = text.split(`{${name}}`).join(vars[name]);
      });
    }
    return text;
  }

  function tp(raw) {
    if (!raw) return t('common.dash');
    const key = `phase.${raw}`;
    const label = t(key);
    return label === key ? raw : label;
  }

  function tl(label, code) {
    const byCode = LANGUAGE_CODES[String(code || '').toLowerCase()];
    const byLabel = LANGUAGE_CODES[String(label || '').toLowerCase()];
    const canonical = byCode || byLabel;
    if (!canonical) return label;
    const key = `language.${canonical}`;
    const translated = t(key);
    return translated === key ? label : translated;
  }

  function tr(message) {
    if (!message) return '';
    for (const [pattern, key, vars] of serverMessages) {
      const match = message.match(pattern);
      if (match) return t(key, vars ? vars(match) : undefined);
    }
    return message;
  }

  function applyLanguage(next) {
    language = translations[next] ? next : DEFAULT_LANGUAGE;
    document.documentElement.lang = language;
    try { window.localStorage.setItem(STORAGE_KEY, language); } catch (e) {}
    document.querySelectorAll('[data-i18n]').forEach(element => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-html]').forEach(element => {
      element.innerHTML = t(element.dataset.i18nHtml);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      element.placeholder = t(element.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
      element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
      element.title = t(element.dataset.i18nTitle);
    });
    const button = document.getElementById('language');
    if (button) {
      button.textContent = language.toUpperCase();
      button.title = t(LANGUAGE_TITLE_KEYS[language]);
    }
    window.dispatchEvent(new CustomEvent('languagechange', { detail: { language } }));
  }

  function initI18n() {
    applyLanguage(language);
    const button = document.getElementById('language');
    if (button) {
      button.addEventListener('click', () => {
        const index = LANGUAGE_ORDER.indexOf(language);
        applyLanguage(LANGUAGE_ORDER[(index + 1) % LANGUAGE_ORDER.length]);
      });
    }
  }

  window.t = t;
  window.tp = tp;
  window.tl = tl;
  window.tr = tr;
  window.applyLanguage = applyLanguage;
  window.initI18n = initI18n;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n);
  } else {
    initI18n();
  }
})();
