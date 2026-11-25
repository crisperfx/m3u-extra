const DEFAULTS = Object.freeze({
    server_url: "",
    ext_token: "",
    button_action: "copy_send",
    select_video: "res=^1280x:for=best",
    select_audio: "for=all",
    select_subtitle: "for=all"
});

const VIDEO_PRESETS = Object.freeze([
    ["", "Geen"],
    ["best", "Beste stream"],
    ["res=^1920x", "1080p - ^1920x"],
    ["res=^1280x", "720p - ^1280x"],
    ["res=^1024x", "576p - ^1024x"],
    ["res=^768x", "432p - ^768x"],
    ["res=^3840x", "4K - ^3840x"],
    ["__custom__", "Aangepast..."]
]);

const LANG_KEYS = Object.freeze(["select_audio", "select_subtitle"]);
const KEYS = Object.keys(DEFAULTS);
const FILTER_KEYS = new Set(["id", "lang", "name", "codecs", "res", "frame", "channel", "range", "url", "segsmin", "segsmax", "plistdurmin", "plistdurmax", "bwmin", "bwmax", "role", "for"]);
const LANG_CODES = Object.freeze({ nl: ["nl", "nld"], nl_be: ["nl-BE"], en: ["en", "eng"] });
const KNOWN_LANG_CODES = new Set(["nl", "nld", "nl-BE", "en", "eng"]);
const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const byId = (id) => document.getElementById(id);
let statusTimer = null;

function setStatus(message, isError = false) {
    const element = byId("status");
    element.textContent = message || "";
    element.classList.toggle("error", Boolean(isError));
    if (statusTimer) clearTimeout(statusTimer);
    if (message && !isError) {
        statusTimer = setTimeout(() => {
            element.textContent = "";
        }, 5000);
    }
}

function hasForModifier(value) {
    return /(^|:)for=/.test(String(value || ""));
}

function splitSelection(value) {
    const stored = String(value || "").trim();
    const match = stored.match(/^(.*?)(:for=(?:best\d*|worst\d*|all))$/i);
    if (match) return [match[1], match[2]];
    return [stored, ""];
}

function cleanCode(value) {
    return String(value || "").trim().replace(/^(['"])(.*)\1$/, "$2").replace(/^\^/, "").replace(/\$$/, "").replace(/\\(.)/g, "$1");
}

function normalizeCustomLangSelection(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const [base, modifier] = splitSelection(raw);
    const unquoted = base.replace(/^(['"])(.*)\1$/, "$2");
    const key = unquoted.split("=")[0].trim().toLowerCase();
    if (key === "lang") {
        const codes = unquoted.slice(5).split("|").map(cleanCode).filter(Boolean);
        if (!codes.length || !codes.every((code) => /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?$/.test(code))) return raw;
        const normalized = "lang=" + codes.map((code) => "^" + escapeRegExp(code) + "$").join("|");
        return modifier ? normalized + modifier : normalized;
    }
    if (FILTER_KEYS.has(key)) return raw;
    const codes = unquoted.split("|").map(cleanCode).filter(Boolean);
    if (!codes.length || !codes.every((code) => /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?$/.test(code))) return raw;
    const normalized = "lang=" + codes.map((code) => "^" + escapeRegExp(code) + "$").join("|");
    return modifier ? normalized + modifier : normalized;
}

function getLangCodes(key) {
    const codes = [];
    Object.keys(LANG_CODES).forEach((lang) => {
        if (byId(key + "_lang_" + lang).checked) codes.push(...LANG_CODES[lang]);
    });
    const extra = byId(key + "_lang_extra").value.trim().split(/\s*\|\s*/).filter(Boolean);
    codes.push(...extra);
    return Array.from(new Set(codes));
}

function selectionBase(key) {
    if (key === "select_video") return byId(key).value.trim();
    const mode = getLangMode(key);
    if (mode === "none") return "";
    if (mode === "all") return "for=all";
    if (mode === "custom") return normalizeCustomLangSelection(byId(key).value.trim());
    const codes = getLangCodes(key);
    return codes.length ? "lang=" + codes.map((code) => "^" + escapeRegExp(code) + "$").join("|") : "";
}

function updateForModifier(key) {
    const base = selectionBase(key);
    const select = byId(key + "_for");
    const disabled = !base || hasForModifier(base);
    select.disabled = disabled;
    if (disabled) select.value = "";
}

function getLangMode(key) {
    if (byId(key + "_mode_none").checked) return "none";
    if (byId(key + "_mode_all").checked) return "all";
    if (byId(key + "_mode_langs").checked) return "langs";
    if (byId(key + "_mode_custom").checked) return "custom";
    return "langs";
}

function setLangMode(key, wanted) {
    ["none", "all", "langs", "custom"].forEach((mode) => {
        byId(key + "_mode_" + mode).checked = mode === wanted;
    });
    updateLangMode(key);
}

function updateLangMode(key) {
    const mode = getLangMode(key);
    byId(key + "_langs").hidden = mode !== "langs";
    byId(key + "_custom").hidden = mode !== "custom";
    const forSelect = byId(key + "_for");
    if (mode === "none" || mode === "all") {
        forSelect.disabled = true;
        forSelect.value = "";
    } else {
        updateForModifier(key);
    }
}

function composeVideoSelection() {
    const base = selectionBase("select_video");
    const modifier = byId("select_video_for").value.trim();
    if (!base || !modifier) return base;
    return hasForModifier(base) ? base : base + ":for=" + modifier;
}

function composeLangSelection(key) {
    const mode = getLangMode(key);
    if (mode === "none") return "";
    if (mode === "all") return "for=all";

    const base = selectionBase(key);
    if (!base) return "";

    const modifier = byId(key + "_for").value.trim();
    if (!base || !modifier) return base;
    return hasForModifier(base) ? base : base + ":for=" + modifier;
}

function composeSelection(key) {
    return key === "select_video" ? composeVideoSelection() : composeLangSelection(key);
}

function setVideoSelection(stored) {
    const [base, modifier] = splitSelection(stored);
    byId("select_video").value = base;
    byId("select_video_for").value = modifier ? modifier.replace(/^:for=/i, "") : "";
    updateForModifier("select_video");
}

function setLangSelection(key, stored) {
    const [base, modifier] = splitSelection(stored);
    let mode;
    if (!base) mode = "none";
    else if (base === "for=all" || base === "all") mode = "all";
    else if (/^lang=/.test(base)) mode = "langs";
    else mode = "custom";

    if (mode === "langs") {
        const codes = base.slice(5).split("|").map(cleanCode).filter(Boolean);
        Object.keys(LANG_CODES).forEach((lang) => {
            byId(key + "_lang_" + lang).checked = LANG_CODES[lang].some((code) => codes.includes(code));
        });
        byId(key + "_lang_extra").value = codes.filter((code) => !KNOWN_LANG_CODES.has(code)).join("|");
        byId(key).value = "";
    } else if (mode === "custom") {
        byId(key).value = base;
    } else {
        byId(key).value = "";
    }

    setLangMode(key, mode);
    byId(key + "_for").value = modifier ? modifier.replace(/^:for=/i, "") : "";
    updateLangMode(key);
}

function setSelection(key, stored) {
    if (key === "select_video") setVideoSelection(stored);
    else setLangSelection(key, stored);
}

function normalizeServer(value, required = true) {
    const raw = String(value || "").trim();
    if (!raw) {
        if (required) throw new Error("Vul een server-URL in");
        return "";
    }
    const url = new URL(raw);
    if (!/^https?:$/.test(url.protocol)) throw new Error("Gebruik http:// of https://");
    return url.origin;
}

function requestOrigin(serverUrl) {
    if (!chrome.permissions || !chrome.permissions.request || !serverUrl) return Promise.resolve(true);
    const origin = new URL(serverUrl).origin + "/*";
    return new Promise((resolve) => {
        chrome.permissions.request({ origins: [origin] }, (granted) => resolve(Boolean(granted)));
    });
}

function getSettings() {
    return new Promise((resolve) => chrome.storage.sync.get(KEYS, resolve));
}

function setSettings(values) {
    return new Promise((resolve) => chrome.storage.sync.set(values, resolve));
}

function buildControls() {
    const videoSelect = byId("select_video_preset");
    videoSelect.replaceChildren();
    VIDEO_PRESETS.forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        videoSelect.append(option);
    });
    videoSelect.addEventListener("change", () => applyVideoPreset());
    byId("select_video").addEventListener("input", () => updateForModifier("select_video"));

    LANG_KEYS.forEach((key) => {
        ["none", "all", "langs", "custom"].forEach((mode) => {
            byId(key + "_mode_" + mode).addEventListener("change", () => updateLangMode(key));
        });
        byId(key + "_lang_extra").addEventListener("input", () => updateLangMode(key));
        byId(key).addEventListener("input", () => updateForModifier(key));
    });
}

function applyVideoPreset() {
    const selected = byId("select_video_preset").value;
    const custom = byId("select_video_custom");
    if (selected === "__custom__") {
        custom.hidden = false;
        byId("select_video").focus();
        updateForModifier("select_video");
        return;
    }
    byId("select_video").value = selected;
    custom.hidden = true;
    updateForModifier("select_video");
}

function syncVideoPreset() {
    const value = byId("select_video").value;
    const isPreset = VIDEO_PRESETS.some(([preset]) => preset === value);
    byId("select_video_preset").value = isPreset ? value : "__custom__";
    byId("select_video_custom").hidden = isPreset;
    updateForModifier("select_video");
}

async function load() {
    const values = await getSettings();
    byId("server_url").value = values.server_url || "";
    byId("ext_token").value = values.ext_token || "";
    byId("button_action").value = values.button_action || DEFAULTS.button_action;
    setSelection("select_video", values.select_video !== undefined ? values.select_video : DEFAULTS.select_video);
    setSelection("select_audio", values.select_audio !== undefined ? values.select_audio : DEFAULTS.select_audio);
    setSelection("select_subtitle", values.select_subtitle !== undefined ? values.select_subtitle : DEFAULTS.select_subtitle);
    syncVideoPreset();
}

function readForm() {
    const button_action = byId("button_action").value;
    return {
        server_url: normalizeServer(byId("server_url").value, button_action !== "copy_only"),
        ext_token: byId("ext_token").value.trim(),
        button_action,
        select_video: composeSelection("select_video"),
        select_audio: composeSelection("select_audio"),
        select_subtitle: composeSelection("select_subtitle")
    };
}

async function save() {
    try {
        const values = readForm();
        const granted = await requestOrigin(values.server_url);
        if (!granted) {
            setStatus("Host-toestemming geweigerd", true);
            return;
        }
        await setSettings(values);
        byId("server_url").value = values.server_url;
        setStatus("Opgeslagen");
    } catch (error) {
        setStatus(error.message || String(error), true);
    }
}

async function testServer() {
    try {
        const server = normalizeServer(byId("server_url").value);
        const granted = await requestOrigin(server);
        if (!granted) {
            setStatus("Host-toestemming geweigerd", true);
            return;
        }
        const response = await fetch(server + "/api/health", { method: "GET" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();
        setStatus(data.ok ? "Server OK" : "Server reageert, maar meldt een fout", !data.ok);
    } catch (error) {
        setStatus("Server niet bereikbaar: " + (error.message || String(error)), true);
    }
}

function reset() {
    byId("server_url").value = "";
    byId("ext_token").value = "";
    byId("button_action").value = DEFAULTS.button_action;
    setSelection("select_video", DEFAULTS.select_video);
    setSelection("select_audio", DEFAULTS.select_audio);
    setSelection("select_subtitle", DEFAULTS.select_subtitle);
    syncVideoPreset();
    setStatus("Standaardwaarden geladen; vul server en token in");
}

document.addEventListener("DOMContentLoaded", () => {
    buildControls();
    byId("save").addEventListener("click", save);
    byId("test_server").addEventListener("click", testServer);
    byId("reset").addEventListener("click", reset);
    load();
});
