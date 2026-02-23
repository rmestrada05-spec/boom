/**
 * Song Studio - Upload & Validate Screen Recording (Step 1 + 2)
 * Supported: .mp4, .mov, .mkv, .avi
 * Validates file (MoviePy server-side); shows error banner or success toast.
 */

// Step 17: Splash screen — full-screen for exactly 5s. Replace with real video player if desired.
// Step 20: After splash, show First Run Setup if not yet completed.
const SPLASH_DURATION_MS = 5000;
const SETUP_STORAGE_KEY = 'songStudioSetupCompleted';
const LAST_MANUAL_SAVE_KEY = 'songStudioLastManualSaveTime';
const AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
(function initSplashAndSetup() {
  const splash = document.getElementById('splash');
  if (splash) {
    setTimeout(() => {
      splash.classList.add('splash--hidden');
      if (localStorage.getItem(SETUP_STORAGE_KEY)) {
        window.__checkCacheSizeWarning?.();
        window.__checkRecoverSession?.();
        window.__checkSystemRequirements?.();
        return;
      }
      const setupScreen = document.getElementById('setup-screen');
      if (setupScreen) {
        setupScreen.hidden = false;
        window.__runSetupCheck?.();
      }
    }, SPLASH_DURATION_MS);
  }
})();

const ALLOWED_EXTENSIONS = new Set(['.mp4', '.mov', '.mkv', '.avi']);
const ALLOWED_TYPES = [
  'video/mp4',
  'video/quicktime',  // .mov
  'video/x-matroska', // .mkv
  'video/avi',
  'video/msvideo',
  'video/x-msvideo',
];

const TOAST_DURATION_MS = 4500;

const $ = (id) => document.getElementById(id);

const fileInput = $('file-input');
const uploadBtn = $('upload-btn');
const loadingState = $('loading-state');
const loadedState = $('loaded-state');
const loadedInfo = $('loaded-info');
const errorState = $('error-state');
const errorMessage = $('error-message');
const errorBanner = $('error-banner');
const errorBannerDetail = $('error-banner-detail');
const retryBtn = $('retry-btn');
const toast = $('toast');
const toastMessage = $('toast-message');
const analyzeBtn = $('analyze-btn');
const analyzingState = $('analyzing-state');
const analysisPanel = $('analysis-panel');
const analysisOutput = $('analysis-output');
const modifyInput = $('modify-input');
const applyModifyBtn = $('apply-modify-btn');
const undoModifyBtn = $('undo-modify-btn');
const redoModifyBtn = $('redo-modify-btn');
const diffSummaryList = $('diff-summary-list');
const diffSummaryEntries = $('diff-summary-entries');
const exportAudioOnlyCheckbox = $('export-audio-only');
const exportFormatChoice = $('export-format-choice');
const saveFinishedBtn = $('save-finished-btn');
const exportResult = $('export-result');
const exportResultPath = $('export-result-path');
const openInFinderBtn = $('open-in-finder-btn');
const analysisPlaceholder = $('analysis-placeholder');
const versionsPlaceholder = $('versions-placeholder');
const voiceLanguageInput = $('voice-language');
const voiceToneInput = $('voice-tone');
const voiceGetPhrasesBtn = $('voice-get-phrases-btn');
const voicePhrasesBox = $('voice-phrases-box');
const voicePhrasesList = $('voice-phrases-list');
const voicePhrasesFallback = $('voice-phrases-fallback');
const voicePhrasesFallbackMessage = $('voice-phrases-fallback-message');
const voicePhrasesFallbackList = $('voice-phrases-fallback-list');
const voiceFileInput = $('voice-file-input');
const voiceUploadBtn = $('voice-upload-btn');
const voiceLoadingState = $('voice-loading-state');
const voiceLoadedState = $('voice-loaded-state');
const voiceLoadedInfo = $('voice-loaded-info');
const voiceAnalysisPlaceholder = $('voice-analysis-placeholder');
const voiceModifyInput = $('voice-modify-input');
const voiceApplyBtn = $('voice-apply-btn');
const voiceUndoBtn = $('voice-undo-btn');
const voiceVersionsSelect = $('voice-versions-select');
const voiceSaveBtn = $('voice-save-btn');
const voiceExportResult = $('voice-export-result');
const voiceExportResultPath = $('voice-export-result-path');
const voiceOpenInFinderBtn = $('voice-open-in-finder-btn');
const layerFileInput = $('layer-file-input');
const layerAddBtn = $('layer-add-btn');
const layerForm = $('layer-form');
const layerMixMode = $('layer-mix-mode');
const layerReplaceTimes = $('layer-replace-times');
const layerStart = $('layer-start');
const layerEnd = $('layer-end');
const layerApplyBtn = $('layer-apply-btn');
const layerLoading = $('layer-loading');
const voiceCacheName = $('voice-cache-name');
const voiceCacheForeverBtn = $('voice-cache-forever-btn');
const addCachedVoiceBtn = $('add-cached-voice-btn');
const cachedVoiceForm = $('cached-voice-form');
const cachedVoiceSelect = $('cached-voice-select');
const cachedVoicePitchFormant = $('cached-voice-pitch-formant');
const cachedVoiceApplyBtn = $('cached-voice-apply-btn');
const cachedVoiceLoading = $('cached-voice-loading');
const saveProjectBtn = $('save-project-btn');
const loadProjectBtn = $('load-project-btn');
const loadProjectInput = $('load-project-input');
const newProjectBtn = $('new-project-btn');
const sessionSongsSelect = $('session-songs-select');
const sessionPlaceholder = $('session-placeholder');
const stemSelect = $('stem-select');
const saveStemBtn = $('save-stem-btn');
const setupScreen = $('setup-screen');
const setupStatus = $('setup-status');
const setupCommands = $('setup-commands');
const setupPipCommand = $('setup-pip-command');
const setupFfmpeg = $('setup-ffmpeg');
const setupAllOk = $('setup-all-ok');
const setupRetryBtn = $('setup-retry-btn');
const setupContinueBtn = $('setup-continue-btn');
const operationError = $('operation-error');
const operationErrorMessage = $('operation-error-message');
const operationErrorToggle = $('operation-error-toggle');
const operationErrorDetail = $('operation-error-detail');
const operationErrorRetry = $('operation-error-retry');
const operationErrorCopy = $('operation-error-copy');
const operationErrorDismiss = $('operation-error-dismiss');
const progressModal = $('progress-modal');
const progressModalTitle = $('progress-modal-title');
const progressModalMessage = $('progress-modal-message');
const progressModalSubtext = $('progress-modal-subtext');
const progressModalSpinner = $('progress-modal-spinner');
const progressModalBarWrap = $('progress-modal-bar-wrap');
const progressModalBar = $('progress-modal-bar');
const progressModalPct = $('progress-modal-pct');
const cacheSizeText = $('cache-size-text');
const cacheClearAllBtn = $('cache-clear-all-btn');
const cacheClearOldBtn = $('cache-clear-old-btn');
const cacheKeepOriginalsBtn = $('cache-keep-originals-btn');
const cacheSizeWarning = $('cache-size-warning');
const cacheSizeWarningLink = $('cache-size-warning-link');
const recoverSessionModal = $('recover-session-modal');
const recoverSessionYes = $('recover-session-yes');
const recoverSessionNo = $('recover-session-no');
const systemRequirementsWarning = $('system-requirements-warning');
const systemRequirementsWarningText = $('system-requirements-warning-text');
const tourOverlay = $('tour-overlay');
const tourCard = $('tour-card');
const tourTitle = $('tour-title');
const tourMessage = $('tour-message');
const tourLinkWrap = $('tour-link-wrap');
const tourLink = $('tour-link');
const tourSkip = $('tour-skip');
const tourBack = $('tour-back');
const tourNext = $('tour-next');
const quitConfirmOverlay = $('quit-confirm-overlay');
const quitConfirmSave = $('quit-confirm-save');
const quitConfirmNo = $('quit-confirm-no');
const quitConfirmCancel = $('quit-confirm-cancel');

const TOUR_STORAGE_KEY = 'songStudioTourCompleted';

/** Step 27: Guided tour steps — targetId = element to point at (null = center). */
const TOUR_STEPS = [
  {
    title: 'What is Vibe Studio?',
    message: 'Vibe Studio lets you upload song clips, analyze parts, and edit with plain-language chat. Save as .vibe projects or export audio and video.',
    linkText: 'Learn more (X / Notion)',
    linkHref: '#',
    targetId: null,
  },
  {
    title: 'Start here',
    message: 'Upload a song clip (screen recording or audio). Supported: .mp4, .mov, .mkv, .avi.',
    targetId: 'upload-btn',
  },
  {
    title: 'Session',
    message: 'Switch between loaded songs here. Add multiple tracks to the same session.',
    targetId: 'session-songs-select',
  },
  {
    title: 'Chat changes',
    message: 'Describe your edit in plain language (e.g. "make bass deeper in the intro") and click Apply.',
    targetId: 'modify-input',
  },
  {
    title: 'Save & export',
    message: 'Export your project as audio/video or save as a .vibe file to continue later.',
    targetId: 'save-finished-btn',
  },
];

const CACHE_SIZE_WARNING_GB = 5;
const MIN_FREE_RAM_GB = 4;

/** Step 22: Buttons to disable during long operations (analysis, stem separation) */
const LONG_OP_BUTTONS = [
  analyzeBtn,
  applyModifyBtn,
  undoModifyBtn,
  saveFinishedBtn,
  uploadBtn,
  layerAddBtn,
  addCachedVoiceBtn,
  cachedVoiceApplyBtn,
  saveStemBtn,
  saveProjectBtn,
  loadProjectBtn,
  newProjectBtn,
].filter(Boolean);

const SETUP_PIP_CMD = 'python3 -m pip install torch torchaudio demucs librosa moviepy pydub ffmpeg-python numpy soundfile';

/** Step 20: First Run Setup — run dependency check and update setup screen UI */
async function runSetupCheck() {
  if (setupStatus) setupStatus.textContent = 'Checking dependencies…';
  if (setupCommands) setupCommands.hidden = true;
  if (setupAllOk) setupAllOk.hidden = true;
  if (setupRetryBtn) setupRetryBtn.hidden = true;
  try {
    const res = await fetch('/api/setup/check');
    const data = await res.json().catch(() => ({}));
    const pythonOk = data.python?.ok !== false && (!data.python?.missing || data.python.missing.length === 0);
    const ffmpegOk = data.ffmpeg?.ok === true;
    const missing = data.python?.missing || [];
    const isMac = (data.platform || '').toLowerCase() === 'darwin';

    if (pythonOk && ffmpegOk) {
      if (setupStatus) setupStatus.textContent = '';
      if (setupAllOk) {
        setupAllOk.textContent = "All dependencies are installed. You're ready to go.";
        setupAllOk.hidden = false;
      }
      if (setupRetryBtn) setupRetryBtn.hidden = true;
    } else {
      if (setupStatus) setupStatus.textContent = 'Some dependencies are missing. Install them, then click Retry or Continue.';
      if (setupCommands) setupCommands.hidden = false;
      if (setupPipCommand) setupPipCommand.textContent = SETUP_PIP_CMD;
      if (setupFfmpeg) setupFfmpeg.hidden = ffmpegOk;
      if (setupRetryBtn) setupRetryBtn.hidden = false;
    }
  } catch (e) {
    if (setupStatus) setupStatus.textContent = 'Could not reach server. Start the app server and click Retry.';
    if (setupCommands) setupCommands.hidden = false;
    if (setupPipCommand) setupPipCommand.textContent = SETUP_PIP_CMD;
    if (setupFfmpeg) setupFfmpeg.hidden = false;
    if (setupRetryBtn) setupRetryBtn.hidden = false;
  }
}
window.__runSetupCheck = runSetupCheck;

if (setupRetryBtn) setupRetryBtn.addEventListener('click', runSetupCheck);
if (setupContinueBtn) {
  setupContinueBtn.addEventListener('click', () => {
    try {
      localStorage.setItem(SETUP_STORAGE_KEY, 'true');
    } catch (_) {}
    if (setupScreen) setupScreen.hidden = true;
    window.__checkCacheSizeWarning?.();
    window.__checkRecoverSession?.();
    window.__checkSystemRequirements?.();
  });
}
window.__checkCacheSizeWarning = checkCacheSizeWarning;

/* ========== Steps 21–23: Reliability & error UI (right after setup & foundation) ========== */
/** Step 21: Operation error popup — friendly message, expandable detail, Retry, Copy Error */
let operationErrorRetryCallback = null;

function showOperationError(message, detail, onRetry) {
  const msg = (message && String(message).trim()) || 'Something went wrong';
  const det = detail != null ? String(detail) : '';
  if (operationErrorMessage) operationErrorMessage.textContent = msg;
  if (operationErrorDetail) {
    operationErrorDetail.textContent = det || '(No technical details)';
    operationErrorDetail.hidden = true;
  }
  if (operationErrorToggle) {
    operationErrorToggle.hidden = !det;
    operationErrorToggle.setAttribute('aria-expanded', 'false');
  }
  operationErrorRetryCallback = typeof onRetry === 'function' ? onRetry : null;
  if (operationError) operationError.hidden = false;
}

function hideOperationError() {
  if (operationError) operationError.hidden = true;
}

if (operationErrorToggle) {
  operationErrorToggle.addEventListener('click', () => {
    const pre = operationErrorDetail;
    const expanded = pre && !pre.hidden;
    if (pre) pre.hidden = expanded;
    if (operationErrorToggle) operationErrorToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
  });
}
if (operationErrorRetry) {
  operationErrorRetry.addEventListener('click', () => {
    hideOperationError();
    if (operationErrorRetryCallback) operationErrorRetryCallback();
  });
}
if (operationErrorCopy) {
  operationErrorCopy.addEventListener('click', () => {
    const msg = operationErrorMessage?.textContent || '';
    const det = operationErrorDetail?.textContent || '';
    const text = det ? `${msg}\n\nTraceback:\n${det}` : msg;
    navigator.clipboard.writeText(text).then(() => showToast('Error copied to clipboard')).catch(() => showToast('Could not copy'));
  });
}
if (operationErrorDismiss) {
  operationErrorDismiss.addEventListener('click', hideOperationError);
}

/** Step 22: Progress modal for long operations — message, optional subtext, optional percentage (0–100) */
function showProgressModal(title, message, subtext, percentage) {
  if (progressModalTitle) progressModalTitle.textContent = title || 'Working…';
  if (progressModalMessage) progressModalMessage.textContent = message || '';
  if (progressModalSubtext) {
    progressModalSubtext.textContent = subtext || '';
    progressModalSubtext.hidden = !subtext;
  }
  const usePct = typeof percentage === 'number' && percentage >= 0 && percentage <= 100;
  if (progressModalSpinner) progressModalSpinner.hidden = usePct;
  if (progressModalBarWrap) progressModalBarWrap.hidden = !usePct;
  if (progressModalPct) {
    progressModalPct.textContent = usePct ? `${Math.round(percentage)}%` : '';
    progressModalPct.hidden = !usePct;
  }
  if (progressModalBar) progressModalBar.style.width = usePct ? `${percentage}%` : '0%';
  if (progressModal) progressModal.hidden = false;
  LONG_OP_BUTTONS.forEach((btn) => { btn.disabled = true; });
}

function setProgressModalPercentage(percentage) {
  const pct = Math.min(100, Math.max(0, Number(percentage)));
  if (progressModalBar) progressModalBar.style.width = `${pct}%`;
  if (progressModalPct) {
    progressModalPct.textContent = `${Math.round(pct)}%`;
    progressModalPct.hidden = false;
  }
  if (progressModalBarWrap) progressModalBarWrap.hidden = false;
  if (progressModalSpinner) progressModalSpinner.hidden = true;
}

function hideProgressModal() {
  if (progressModal) progressModal.hidden = true;
  LONG_OP_BUTTONS.forEach((btn) => { btn.disabled = false; });
}

/** Step 22: For stem separation (Demucs) — call showProgressModal then setProgressModalPercentage(pct) as progress arrives; hideProgressModal() when done. */
function showStemProgressModal(percentage) {
  const pct = typeof percentage === 'number' ? Math.round(percentage) : 0;
  const msg = pct > 0 ? `Separating stems… ${pct}%` : 'Separating stems…';
  showProgressModal(
    'Separating stems',
    msg,
    'This may take 1–2 minutes the first time.',
    pct
  );
}

function updateStemProgressModal(percentage) {
  setProgressModalPercentage(percentage);
  if (progressModalMessage) {
    const pct = Math.round(Math.min(100, Math.max(0, Number(percentage))));
    progressModalMessage.textContent = `Separating stems… ${pct}%`;
  }
}

/** Step 23: Cache management */
async function fetchCacheSize() {
  const res = await fetch('/api/cache/size');
  const data = await res.json().catch(() => ({}));
  return res.ok ? { bytes: data.bytes || 0, bytesFormatted: data.bytesFormatted || '0 B' } : { bytes: 0, bytesFormatted: '0 B' };
}

async function refreshCacheSizeDisplay() {
  const { bytes, bytesFormatted } = await fetchCacheSize();
  if (cacheSizeText) cacheSizeText.textContent = `Cache using ${bytesFormatted}`;
  if (cacheSizeWarning) cacheSizeWarning.hidden = bytes <= CACHE_SIZE_WARNING_GB * 1e9;
  return bytes;
}

function checkCacheSizeWarning() {
  fetchCacheSize().then(({ bytes }) => {
    if (cacheSizeWarning) cacheSizeWarning.hidden = bytes <= CACHE_SIZE_WARNING_GB * 1e9;
  });
}

function switchToCustomizeTab() {
  const tab = document.querySelector('.tab[data-tab="customize"]');
  if (tab) tab.click();
}

async function clearCache(mode, confirmMessage) {
  if (!confirm(confirmMessage)) return;
  try {
    const res = await fetch('/api/cache/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Clear failed', data.detail, null);
      return;
    }
    await refreshCacheSizeDisplay();
    showToast(`Cache cleared. Now using ${data.bytesFormatted || '0 B'}.`);
  } catch (e) {
    showOperationError(e.message || 'Clear failed', e.stack || e.message, null);
  }
}

if (cacheClearAllBtn) {
  cacheClearAllBtn.addEventListener('click', () => {
    clearCache('all', 'This will delete all cached songs, exports, and voices. Continue?');
  });
}
if (cacheClearOldBtn) {
  cacheClearOldBtn.addEventListener('click', () => {
    clearCache('old_versions', 'This will remove exports and version history. Originals and voices are kept. Continue?');
  });
}
if (cacheKeepOriginalsBtn) {
  cacheKeepOriginalsBtn.addEventListener('click', () => {
    clearCache('keep_originals', 'This will remove everything except original song files. Continue?');
  });
}
if (cacheSizeWarningLink) {
  cacheSizeWarningLink.addEventListener('click', (e) => {
    e.preventDefault();
    switchToCustomizeTab();
  });
}

/* ========== Steps 27–30: Polish & UX (tour, export settings, quit confirm) — with Step 8 ========== */
/** Step 27: Guided tour — first launch only */
let tourStepIndex = 0;

function positionTourCard(targetId) {
  if (!tourCard) return;
  const card = tourCard;
  if (!targetId) {
    card.style.left = '50%';
    card.style.top = '50%';
    card.style.transform = 'translate(-50%, -50%)';
    return;
  }
  const el = document.getElementById(targetId);
  if (!el) {
    card.style.left = '50%';
    card.style.top = '50%';
    card.style.transform = 'translate(-50%, -50%)';
    return;
  }
  el.scrollIntoView({ behavior: 'instant', block: 'center' });
  requestAnimationFrame(() => {
    const rect = el.getBoundingClientRect();
    const cardWidth = 320;
    const cardHeight = 220;
    const gap = 12;
    let top = rect.bottom + gap;
    let left = rect.left + (rect.width / 2) - (cardWidth / 2);
    if (top + cardHeight > window.innerHeight - 20) top = rect.top - cardHeight - gap;
    if (top < 20) top = 20;
    if (left < 20) left = 20;
    if (left + cardWidth > window.innerWidth - 20) left = window.innerWidth - cardWidth - 20;
    card.style.left = `${left}px`;
    card.style.top = `${top}px`;
    card.style.transform = 'none';
  });
}

function showTourStep(index) {
  const step = TOUR_STEPS[index];
  if (!step || !tourOverlay) return;
  tourStepIndex = index;
  if (tourTitle) tourTitle.textContent = step.title;
  if (tourMessage) tourMessage.textContent = step.message;
  if (tourLinkWrap && tourLink) {
    if (step.linkText && step.linkHref) {
      tourLink.textContent = step.linkText;
      tourLink.href = step.linkHref;
      tourLinkWrap.hidden = false;
    } else {
      tourLinkWrap.hidden = true;
    }
  }
  if (tourBack) tourBack.hidden = index === 0;
  if (tourNext) {
    tourNext.textContent = index === TOUR_STEPS.length - 1 ? 'Get started' : 'Next';
  }
  positionTourCard(step.targetId);
}

function endTour() {
  try { localStorage.setItem(TOUR_STORAGE_KEY, 'true'); } catch (_) {}
  if (tourOverlay) tourOverlay.hidden = true;
}

function startTourIfFirstLaunch() {
  try {
    if (localStorage.getItem(TOUR_STORAGE_KEY)) return;
  } catch (_) {}
  if (!tourOverlay) return;
  tourStepIndex = 0;
  tourOverlay.hidden = false;
  showTourStep(0);
}

window.__startTourIfFirstLaunch = startTourIfFirstLaunch;

if (tourSkip) tourSkip.addEventListener('click', endTour);
if (tourBack) tourBack.addEventListener('click', () => { if (tourStepIndex > 0) showTourStep(tourStepIndex - 1); });
if (tourNext) {
  tourNext.addEventListener('click', () => {
    if (tourStepIndex >= TOUR_STEPS.length - 1) endTour();
    else showTourStep(tourStepIndex + 1);
  });
}

/** Path of current song (for analysis, modifications, layers, export). */
let lastValidatedPath = null;

/** Step 24: In-memory undo/redo stack for chat changes (last 10 actions). */
const MAX_UNDO_STACK = 10;
let undoStack = [];
let redoStack = [];
let currentModificationCount = 0;

/** Step 18: Multi-song session — list of { path, name, duration } (duration in seconds). */
let sessionSongs = [];

/** Step 12: Last uploaded voice file path (Voice tab). */
let lastVoicePath = null;
let lastVoiceExportUrl = null;

/** Last export download URL and filename (for Open in Finder). */
let lastExportDownloadUrl = null;
let lastExportFilename = null;

/** Step 29: Unsaved changes — true after apply/undo/redo until save or load. */
let projectDirty = false;
let allowUnload = false;

/** Step 8: Theme presets (background, panels, accent, text) — polish & UX. */
const THEME_PRESETS = {
  fl_studio: {
    name: 'FL Studio',
    bg: '#1E1E1E',
    panelBg: '#252526',
    bgInput: '#2D2D30',
    accent: '#FF8000',
    accentText: '#000000',
    text: '#E0E0E0',
    textMuted: '#9D9D9D',
    border: '#3C3C3C',
  },
  ocean: {
    name: 'Ocean',
    bg: '#0D1B24',
    panelBg: '#132D3A',
    bgInput: '#1A3D4D',
    accent: '#00A8CC',
    accentText: '#FFFFFF',
    text: '#E0EDF2',
    textMuted: '#8BA4B0',
    border: '#2A4A5A',
  },
  forest: {
    name: 'Forest',
    bg: '#1A2419',
    panelBg: '#243824',
    bgInput: '#2E4A2E',
    accent: '#4CAF50',
    accentText: '#FFFFFF',
    text: '#E0EDE0',
    textMuted: '#8BA88B',
    border: '#3A4A3A',
  },
  sunset: {
    name: 'Sunset',
    bg: '#241A14',
    panelBg: '#382818',
    bgInput: '#4A3524',
    accent: '#FF6B35',
    accentText: '#FFFFFF',
    text: '#F2E6E0',
    textMuted: '#B09D8B',
    border: '#4A3A2A',
  },
  mono: {
    name: 'Mono',
    bg: '#1A1A1A',
    panelBg: '#262626',
    bgInput: '#333333',
    accent: '#A0A0A0',
    accentText: '#1A1A1A',
    text: '#D0D0D0',
    textMuted: '#808080',
    border: '#404040',
  },
  cherry: {
    name: 'Cherry',
    bg: '#24161A',
    panelBg: '#381E24',
    bgInput: '#4A2830',
    accent: '#E91E63',
    accentText: '#FFFFFF',
    text: '#F2E0E4',
    textMuted: '#B08B96',
    border: '#4A3038',
  },
  midnight: {
    name: 'Midnight',
    bg: '#0F0E1A',
    panelBg: '#1A1830',
    bgInput: '#252240',
    accent: '#7C4DFF',
    accentText: '#FFFFFF',
    text: '#E0DDF2',
    textMuted: '#8B85B0',
    border: '#2A2840',
  },
  lavender: {
    name: 'Lavender',
    bg: '#1E1A24',
    panelBg: '#2D2438',
    bgInput: '#3D324A',
    accent: '#B388FF',
    accentText: '#1A1A1A',
    text: '#EDE0F2',
    textMuted: '#9D8BB0',
    border: '#4A4055',
  },
};

let currentThemeId = 'fl_studio';

function applyTheme(preset) {
  const root = document.documentElement;
  root.style.setProperty('--bg', preset.bg);
  root.style.setProperty('--bg-panel', preset.panelBg);
  root.style.setProperty('--bg-input', preset.bgInput);
  root.style.setProperty('--accent', preset.accent);
  root.style.setProperty('--accent-text', preset.accentText);
  root.style.setProperty('--text', preset.text);
  root.style.setProperty('--text-muted', preset.textMuted);
  root.style.setProperty('--border', preset.border);
}

function loadThemeSettings() {
  fetch('/api/settings')
    .then((res) => (res.ok ? res.json() : {}))
    .then((data) => {
      const id = data.theme || 'fl_studio';
      const preset = THEME_PRESETS[id] || THEME_PRESETS.fl_studio;
      currentThemeId = id;
      applyTheme(preset);
      renderThemeSwatches();
      applyExportSettings(data);
    })
    .catch(() => {
      applyTheme(THEME_PRESETS.fl_studio);
      renderThemeSwatches();
    });
}

function applyExportSettings(data) {
  if (exportAudioOnlyCheckbox) {
    if (typeof data.exportAudioOnly === 'boolean') exportAudioOnlyCheckbox.checked = data.exportAudioOnly;
    if (exportFormatChoice) exportFormatChoice.hidden = !exportAudioOnlyCheckbox.checked;
  }
  const format = data.exportFormat === 'wav' ? 'wav' : 'mp3';
  const radio = document.querySelector(`input[name="export-format"][value="${format}"]`);
  if (radio) radio.checked = true;
}

function persistExportSettings() {
  const exportAudioOnly = exportAudioOnlyCheckbox?.checked ?? false;
  const format = document.querySelector('input[name="export-format"]:checked')?.value ?? 'mp3';
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ exportAudioOnly, exportFormat: format }),
  }).catch(() => {});
}

/** Step 29: Quit confirmation when unsaved changes — Save / Don't save / Cancel */
function showQuitConfirmModal() {
  if (quitConfirmOverlay) quitConfirmOverlay.hidden = false;
}
function hideQuitConfirmModal() {
  if (quitConfirmOverlay) quitConfirmOverlay.hidden = true;
}
function onQuitConfirmSave() {
  hideQuitConfirmModal();
  saveProjectAs();
}
function onQuitConfirmNo() {
  allowUnload = true;
  setTimeout(() => { allowUnload = false; }, 2000);
  hideQuitConfirmModal();
  showToast('Close the window again to exit without saving');
  window.close();
}
function onQuitConfirmCancel() {
  hideQuitConfirmModal();
}

function renderThemeSwatches() {
  const container = $('theme-swatches');
  if (!container) return;
  container.innerHTML = '';
  Object.entries(THEME_PRESETS).forEach(([id, preset]) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-swatch' + (id === currentThemeId ? ' theme-swatch--active' : '');
    btn.setAttribute('data-theme-id', id);
    btn.setAttribute('aria-pressed', id === currentThemeId);
    const patch = document.createElement('div');
    patch.className = 'theme-swatch-patch';
    patch.style.background = preset.accent;
    const label = document.createElement('span');
    label.textContent = preset.name;
    btn.appendChild(patch);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectTheme(id));
    container.appendChild(btn);
  });
}

function selectTheme(id) {
  const preset = THEME_PRESETS[id] || THEME_PRESETS.fl_studio;
  currentThemeId = id;
  applyTheme(preset);
  renderThemeSwatches();
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme: id }),
  }).catch(() => {});
}

function showSection(section) {
  loadingState.hidden = section !== 'loading';
  loadedState.hidden = section !== 'loaded';
  errorState.hidden = section !== 'error';
  if (analysisPlaceholder) analysisPlaceholder.hidden = section === 'loaded';
}

/**
 * Show or hide the red error banner (Step 9: used for every upload/validation failure).
 * @param {boolean} show - Whether to show the banner
 * @param {string} [detail] - Detailed error reason (e.g. from server validation); shown below main message
 */
function showErrorBanner(show, detail) {
  errorBanner.hidden = !show;
  if (errorBannerDetail) {
    if (show && detail) {
      errorBannerDetail.textContent = detail;
      errorBannerDetail.hidden = false;
    } else {
      errorBannerDetail.textContent = '';
      errorBannerDetail.hidden = true;
    }
  }
}

function showToast(message) {
  toastMessage.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast._tid);
  showToast._tid = setTimeout(() => {
    toast.hidden = true;
  }, TOAST_DURATION_MS);
}

function showError(msg) {
  errorMessage.textContent = msg;
  showSection('error');
}

function formatDuration(seconds) {
  if (Number.isFinite(seconds) && seconds >= 0) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  }
  return '0:00';
}

function getExtension(filename) {
  const i = filename.lastIndexOf('.');
  return i >= 0 ? filename.slice(i).toLowerCase() : '';
}

function validateFile(file) {
  const ext = getExtension(file.name);
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return `Unsupported format. Use: .mp4, .mov, .mkv, .avi (got ${ext || 'no extension'}).`;
  }
  const typeOk = ALLOWED_TYPES.some(t => file.type === t) || ALLOWED_EXTENSIONS.has(ext);
  if (!typeOk && file.type) {
    return `Unsupported file type: ${file.type}. Use .mp4, .mov, .mkv, or .avi.`;
  }
  return null;
}

function getVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';

    const cleanup = () => {
      video.removeEventListener('loadedmetadata', onMeta);
      video.removeEventListener('error', onErr);
      URL.revokeObjectURL(url);
    };

    const onMeta = () => {
      const dur = video.duration;
      cleanup();
      resolve(Number.isFinite(dur) ? dur : 0);
    };

    const onErr = () => {
      cleanup();
      reject(new Error('Could not read video duration'));
    };

    video.addEventListener('loadedmetadata', onMeta);
    video.addEventListener('error', onErr);
    video.src = url;
  });
}

async function saveToCache(file) {
  const formData = new FormData();
  formData.append('recording', file);

  const res = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || data.message || `Upload failed: ${res.status}`);
    err.detail = data.detail;
    throw err;
  }
  return {
    cachePath: data.path ?? null,
    originalName: data.originalName ?? file.name,
    validation: data.validation ?? null,
  };
}

async function handleFileSelect(file) {
  const err = validateFile(file);
  if (err) {
    showError(err);
    return;
  }

  showSection('loading');

  try {
    const [duration, cacheResult] = await Promise.all([
      getVideoDuration(file),
      saveToCache(file).catch((e) => ({ originalName: file.name, validation: null, error: e.message, detail: e.detail || e.stack })),
    ]);

    const displayDuration = formatDuration(duration);
    const name = cacheResult.originalName ?? file.name;
    const validation = cacheResult.validation;

    if (cacheResult.error) {
      showSection('');
      fileInput.value = '';
      showOperationError(cacheResult.error, cacheResult.detail, () => fileInput?.click());
      return;
    }

    // Step 2/9: validation result from server (corruption checks); show detailed reason on failure
    if (validation && validation.ok === false) {
      showSection('');
      fileInput.value = '';
      showOperationError(validation.error || 'Validation failed.', null, () => fileInput?.click());
      return;
    }

    showErrorBanner(false);
    addSongToSession(cacheResult.cachePath ?? null, name, duration);
    loadedInfo.textContent = `${name} – ${displayDuration}`;
    analysisPanel.hidden = true;
    analyzingState.hidden = true;
    if (analyzeBtn) analyzeBtn.hidden = false;
    showSection('loaded');
    fetchVersions();

    if (validation && validation.ok === true && validation.durationFormatted) {
      showToast(`File validated successfully (Duration: ${validation.durationFormatted})`);
    }
  } catch (e) {
    showSection('');
    showOperationError(e.message || 'Failed to load or validate the file.', e.detail || e.stack, () => fileInput?.click());
  } finally {
    fileInput.value = '';
  }
}

uploadBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  handleFileSelect(file);
});

if (sessionSongsSelect) {
  sessionSongsSelect.addEventListener('change', () => {
    const path = sessionSongsSelect.value;
    if (path) switchToSong(path);
  });
}

retryBtn.addEventListener('click', () => {
  showErrorBanner(false);
  showSection('');
  fileInput.value = '';
});

/** Step 18: Multi-song session — add song to session (dedupe by path), refresh dropdown, set as current. */
function addSongToSession(path, name, durationSec) {
  if (!path) return;
  const existing = sessionSongs.find((s) => s.path === path);
  if (!existing) {
    sessionSongs.push({ path, name: name || path, duration: durationSec });
  } else {
    existing.name = name || existing.name;
    if (durationSec != null) existing.duration = durationSec;
  }
  lastValidatedPath = path;
  refreshSessionDropdown();
}

/** Step 18: Populate session dropdown from sessionSongs; set selection to lastValidatedPath. */
function refreshSessionDropdown() {
  if (!sessionSongsSelect) return;
  const selectedPath = lastValidatedPath;
  sessionSongsSelect.innerHTML = '';
  if (sessionSongs.length === 0) {
    sessionSongsSelect.appendChild(new Option('No songs loaded', '', true, true));
    sessionSongsSelect.disabled = true;
    if (sessionPlaceholder) sessionPlaceholder.hidden = false;
    return;
  }
  if (sessionPlaceholder) sessionPlaceholder.hidden = true;
  sessionSongsSelect.disabled = false;
  sessionSongs.forEach((s) => {
    const label = `${s.name}${s.duration != null ? ` (${formatDuration(s.duration)})` : ''}`;
    sessionSongsSelect.appendChild(new Option(label, s.path));
  });
  if (selectedPath && sessionSongs.some((s) => s.path === selectedPath)) {
    sessionSongsSelect.value = selectedPath;
  } else if (sessionSongs.length > 0) {
    lastValidatedPath = sessionSongs[0].path;
    sessionSongsSelect.value = lastValidatedPath;
  }
}

/** Step 18: Switch current song; reload versions, reset analysis. */
function switchToSong(path) {
  const entry = sessionSongs.find((s) => s.path === path);
  if (!entry) return;
  lastValidatedPath = path;
  undoStack = [];
  redoStack = [];
  refreshSessionDropdown();
  loadedInfo.textContent = `${entry.name} – ${entry.duration != null ? formatDuration(entry.duration) : '—'}`;
  loadedState.hidden = false;
  if (loadingState) loadingState.hidden = true;
  if (errorState) errorState.hidden = true;
  if (analysisPlaceholder) analysisPlaceholder.hidden = true;
  if (analysisPanel) analysisPanel.hidden = true;
  if (analysisOutput) analysisOutput.value = '';
  if (analyzeBtn) analyzeBtn.hidden = false;
  fetchVersions();
  updateUndoRedoButtons();
}

function renderDiffSummaryList(modifications) {
  if (!diffSummaryEntries) return;
  currentModificationCount = (modifications && modifications.length) || 0;
  diffSummaryEntries.innerHTML = '';
  if (!modifications || modifications.length === 0) {
    if (diffSummaryList) diffSummaryList.hidden = true;
    if (versionsPlaceholder) versionsPlaceholder.hidden = false;
    return;
  }
  modifications.forEach((m) => {
    const li = document.createElement('li');
    li.textContent = m.diffSummary || m.description;
    diffSummaryEntries.appendChild(li);
  });
  if (diffSummaryList) diffSummaryList.hidden = false;
  if (versionsPlaceholder) versionsPlaceholder.hidden = true;
}

/** Step 24: Update Undo/Redo button state from in-memory stacks and server modification count. */
function updateUndoRedoButtons() {
  const hasPath = !!lastValidatedPath;
  if (undoModifyBtn) {
    undoModifyBtn.hidden = !hasPath;
    undoModifyBtn.disabled = !hasPath || currentModificationCount === 0;
  }
  if (redoModifyBtn) {
    redoModifyBtn.hidden = !hasPath;
    redoModifyBtn.disabled = !hasPath || redoStack.length === 0;
  }
}

async function fetchVersions() {
  if (!lastValidatedPath) return;
  try {
    const res = await fetch(`/api/versions?path=${encodeURIComponent(lastValidatedPath)}`);
    const data = await res.json().catch(() => ({}));
    if (res.ok && Array.isArray(data.modifications)) {
      renderDiffSummaryList(data.modifications);
    }
    updateUndoRedoButtons();
  } catch {
    renderDiffSummaryList([]);
    updateUndoRedoButtons();
  }
}

async function runAnalysis() {
  if (!lastValidatedPath) return;
  analyzeBtn.hidden = true;
  analyzingState.hidden = false;
  analysisPanel.hidden = true;
  showProgressModal(
    'Analyzing song parts',
    'Analyzing song parts…',
    'This may take 1–2 minutes.',
    null
  );
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastValidatedPath }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Analysis failed', data.detail, runAnalysis);
      return;
    }
    analysisOutput.value = data.analysis ?? '';
    analysisPanel.hidden = false;
    await fetchVersions();
    showToast(`Analysis complete (Duration: ${data.durationFormatted ?? '—'})`);
  } catch (e) {
    showOperationError(e.message || 'Analysis failed', e.stack || e.message, runAnalysis);
  } finally {
    hideProgressModal();
    analyzingState.hidden = true;
    analyzeBtn.hidden = false;
  }
}

async function applyModification() {
  const description = modifyInput?.value?.trim();
  if (!description || !lastValidatedPath) return;
  applyModifyBtn.disabled = true;
  try {
    const res = await fetch('/api/modify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastValidatedPath, description }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Modification failed', data.detail, applyModification);
      return;
    }
    modifyInput.value = '';
    const entry = { description, path: lastValidatedPath };
    undoStack.push(entry);
    if (undoStack.length > MAX_UNDO_STACK) undoStack.shift();
    redoStack = [];
    renderDiffSummaryList(data.modifications);
    updateUndoRedoButtons();
    projectDirty = true;
    showToast(`Applied: ${data.diffSummary ?? 'change saved'}`);
    runAutosave();
  } catch (e) {
    showOperationError(e.message || 'Modification failed', e.stack || e.message, applyModification);
  } finally {
    applyModifyBtn.disabled = false;
  }
}

async function undoModification() {
  if (!lastValidatedPath) return;
  undoModifyBtn.disabled = true;
  try {
    const res = await fetch('/api/undo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastValidatedPath }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Undo failed', data.detail, undoModification);
      return;
    }
    if (undoStack.length > 0) {
      const entry = undoStack.pop();
      redoStack.push(entry);
    }
    renderDiffSummaryList(data.modifications);
    updateUndoRedoButtons();
    projectDirty = true;
    showToast('Reverted to previous version');
    runAutosave();
  } catch (e) {
    showOperationError(e.message || 'Undo failed', e.stack || e.message, undoModification);
  } finally {
    undoModifyBtn.disabled = false;
  }
}

async function redoModification() {
  if (!lastValidatedPath || redoStack.length === 0) return;
  const entry = redoStack.pop();
  if (!entry || entry.path !== lastValidatedPath) return;
  redoModifyBtn.disabled = true;
  try {
    const res = await fetch('/api/modify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: entry.path, description: entry.description }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      redoStack.push(entry);
      showOperationError(data.error || 'Redo failed', data.detail, () => redoModification());
      return;
    }
    undoStack.push(entry);
    if (undoStack.length > MAX_UNDO_STACK) undoStack.shift();
    renderDiffSummaryList(data.modifications);
    updateUndoRedoButtons();
    projectDirty = true;
    showToast(`Redone: ${data.diffSummary ?? 'change saved'}`);
    runAutosave();
  } catch (e) {
    redoStack.push(entry);
    showOperationError(e.message || 'Redo failed', e.stack || e.message, () => redoModification());
  } finally {
    redoModifyBtn.disabled = false;
  }
}

function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function saveFinishedProduct() {
  if (!lastValidatedPath) return;
  const exportAudioOnly = exportAudioOnlyCheckbox?.checked ?? false;
  const format = document.querySelector('input[name="export-format"]:checked')?.value ?? 'mp3';
  saveFinishedBtn.disabled = true;
  exportResult.hidden = true;
  try {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: lastValidatedPath,
        exportAudioOnly,
        format: exportAudioOnly ? format : undefined,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Export failed', data.detail, saveFinishedProduct);
      return;
    }
    const baseUrl = window.location.origin;
    const downloadUrl = data.downloadUrl ? baseUrl + data.downloadUrl : null;
    lastExportDownloadUrl = downloadUrl;
    lastExportFilename = data.filename || '';
    if (downloadUrl) {
      triggerDownload(downloadUrl, data.filename);
    }
    exportResultPath.textContent = `Saved as ${data.filename || data.path || 'file'}`;
    exportResult.hidden = false;
    persistExportSettings();
    showToast('Export saved');
  } catch (e) {
    showOperationError(e.message || 'Export failed', e.stack || e.message, saveFinishedProduct);
  } finally {
    saveFinishedBtn.disabled = false;
  }
}

function openInFinder() {
  if (lastExportDownloadUrl) {
    window.open(lastExportDownloadUrl, '_blank', 'noopener');
  }
}

/** Step 13: Get phonetically balanced phrases for the entered language */
async function getVoicePhrases() {
  const lang = voiceLanguageInput?.value?.trim() || '';
  voiceGetPhrasesBtn.disabled = true;
  if (voicePhrasesBox) voicePhrasesBox.hidden = true;
  if (voicePhrasesFallback) voicePhrasesFallback.hidden = true;
  try {
    const res = await fetch(`/api/voice/phrases?lang=${encodeURIComponent(lang)}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showToast(data.error || 'Could not load phrases');
      return;
    }
    if (data.fallback) {
      if (voicePhrasesFallbackMessage) voicePhrasesFallbackMessage.textContent = data.message || '';
      if (voicePhrasesFallbackList) {
        voicePhrasesFallbackList.innerHTML = '';
        (data.suggestedPhrases || []).forEach((p) => {
          const li = document.createElement('li');
          li.textContent = p;
          voicePhrasesFallbackList.appendChild(li);
        });
      }
      if (voicePhrasesFallback) voicePhrasesFallback.hidden = false;
    } else {
      if (voicePhrasesList) {
        voicePhrasesList.innerHTML = '';
        (data.phrases || []).forEach((p) => {
          const li = document.createElement('li');
          li.textContent = p;
          voicePhrasesList.appendChild(li);
        });
      }
      if (voicePhrasesBox) voicePhrasesBox.hidden = false;
    }
  } catch (e) {
    showToast(e.message || 'Could not load phrases');
  } finally {
    voiceGetPhrasesBtn.disabled = false;
  }
}

if (voiceGetPhrasesBtn) voiceGetPhrasesBtn.addEventListener('click', getVoicePhrases);

/** Step 12: Voice tab — upload, modify, versions dropdown, save */
async function handleVoiceFileSelect(file) {
  if (!file) return;
  voiceLoadingState.hidden = false;
  voiceLoadedState.hidden = true;
  if (voiceAnalysisPlaceholder) voiceAnalysisPlaceholder.hidden = false;
  showErrorBanner(false);
  try {
    const formData = new FormData();
    formData.append('voice', file);
    const res = await fetch('/api/voice/upload', { method: 'POST', body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || `Upload failed: ${res.status}`, data.detail, () => voiceFileInput?.click());
      return;
    }
    lastVoicePath = data.path || null;
    voiceLoadedInfo.textContent = data.originalName || file.name || 'Voice loaded';
    voiceLoadedState.hidden = false;
    if (voiceAnalysisPlaceholder) voiceAnalysisPlaceholder.hidden = true;
    await renderVoiceVersionsDropdown();
    showToast('Voice recording loaded');
  } catch (e) {
    showOperationError(e.message || 'Voice upload failed', e.stack || e.message, () => voiceFileInput?.click());
  } finally {
    voiceLoadingState.hidden = true;
    voiceFileInput.value = '';
  }
}

function renderVoiceVersionsDropdown() {
  if (!voiceVersionsSelect || !lastVoicePath) return;
  fetch(`/api/voice/versions?path=${encodeURIComponent(lastVoicePath)}`)
    .then((r) => r.json())
    .then((data) => {
      const list = data.modifications || [];
      voiceVersionsSelect.innerHTML = '';
      voiceVersionsSelect.appendChild(new Option('Original', 'original'));
      list.forEach((m, i) => {
        voiceVersionsSelect.appendChild(new Option(`v${i + 1} – ${m.diffSummary || m.description}`, m.id));
      });
      voiceUndoBtn.hidden = list.length === 0;
    })
    .catch(() => {});
}

async function applyVoiceModification() {
  const description = voiceModifyInput?.value?.trim();
  if (!description || !lastVoicePath) return;
  voiceApplyBtn.disabled = true;
  try {
    const res = await fetch('/api/voice/modify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastVoicePath, description }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Modification failed', data.detail, applyVoiceModification);
      return;
    }
    voiceModifyInput.value = '';
    await renderVoiceVersionsDropdown();
    showToast(`Applied: ${data.diffSummary ?? 'change saved'}`);
  } catch (e) {
    showOperationError(e.message || 'Modification failed', e.stack || e.message, applyVoiceModification);
  } finally {
    voiceApplyBtn.disabled = false;
  }
}

async function undoVoiceModification() {
  if (!lastVoicePath) return;
  voiceUndoBtn.disabled = true;
  try {
    const res = await fetch('/api/voice/undo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastVoicePath }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Undo failed', data.detail, undoVoiceModification);
      return;
    }
    await renderVoiceVersionsDropdown();
    showToast('Reverted to previous version');
  } catch (e) {
    showOperationError(e.message || 'Undo failed', e.stack || e.message, undoVoiceModification);
  } finally {
    voiceUndoBtn.disabled = false;
  }
}

async function saveVoice() {
  if (!lastVoicePath) return;
  voiceSaveBtn.disabled = true;
  voiceExportResult.hidden = true;
  try {
    const res = await fetch('/api/voice/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastVoicePath }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Export failed', data.detail, saveVoice);
      return;
    }
    const baseUrl = window.location.origin;
    const url = data.downloadUrl ? baseUrl + data.downloadUrl : null;
    lastVoiceExportUrl = url;
    if (url) triggerDownload(url, data.filename);
    voiceExportResultPath.textContent = `Saved as ${data.filename || data.path || 'file'}`;
    voiceExportResult.hidden = false;
    showToast('Voice saved');
  } catch (e) {
    showOperationError(e.message || 'Export failed', e.stack || e.message, saveVoice);
  } finally {
    voiceSaveBtn.disabled = false;
  }
}

if (voiceUploadBtn) voiceUploadBtn.addEventListener('click', () => voiceFileInput?.click());
if (voiceFileInput) voiceFileInput.addEventListener('change', () => {
  const file = voiceFileInput.files?.[0];
  if (file) handleVoiceFileSelect(file);
});
if (voiceApplyBtn) voiceApplyBtn.addEventListener('click', applyVoiceModification);
if (voiceUndoBtn) voiceUndoBtn.addEventListener('click', undoVoiceModification);
if (voiceSaveBtn) voiceSaveBtn.addEventListener('click', saveVoice);
if (voiceOpenInFinderBtn) voiceOpenInFinderBtn.addEventListener('click', () => {
  if (lastVoiceExportUrl) window.open(lastVoiceExportUrl, '_blank', 'noopener');
});

/** Step 15: Cache This Voice Forever */
async function cacheVoiceForever() {
  if (!lastVoicePath) {
    showToast('Upload a voice recording first');
    return;
  }
  if (voiceCacheForeverBtn) voiceCacheForeverBtn.disabled = true;
  try {
    const res = await fetch('/api/voice/cache', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastVoicePath, name: (voiceCacheName?.value || '').trim() || undefined }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Cache failed', data.detail, cacheVoiceForever);
      return;
    }
    showToast(`Voice cached forever as ${data.name || data.path || 'file'}`);
    if (voiceCacheName) voiceCacheName.value = '';
  } catch (e) {
    showOperationError(e.message || 'Cache failed', e.stack || e.message, cacheVoiceForever);
  } finally {
    if (voiceCacheForeverBtn) voiceCacheForeverBtn.disabled = false;
  }
}
if (voiceCacheForeverBtn) voiceCacheForeverBtn.addEventListener('click', cacheVoiceForever);

/** Step 14: Add Audio/Video Layer */
function showLayerForm(show) {
  if (layerForm) layerForm.hidden = !show;
  if (layerMixMode && show) {
    const isReplace = layerMixMode.value === 'replace';
    if (layerReplaceTimes) layerReplaceTimes.hidden = !isReplace;
  }
}

async function addLayer() {
  const file = layerFileInput?.files?.[0];
  if (!file) {
    showToast('Select a file first');
    return;
  }
  if (!lastValidatedPath) {
    showToast('Load a song in Studio first');
    return;
  }
  layerApplyBtn.disabled = true;
  if (layerLoading) layerLoading.hidden = false;
  try {
    const formData = new FormData();
    formData.append('layer', file);
    formData.append('path', lastValidatedPath);
    formData.append('mixMode', layerMixMode?.value || 'overlay50');
    if (layerMixMode?.value === 'replace') {
      formData.append('startTime', String(layerStart?.value ?? 0));
      formData.append('endTime', String(layerEnd?.value ?? 10));
    }
    const res = await fetch('/api/layer/add', { method: 'POST', body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Add layer failed', data.detail, addLayer);
      return;
    }
    renderDiffSummaryList(data.modifications);
    showLayerForm(false);
    layerFileInput.value = '';
    showToast(data.diffSummary || 'Layer added');
    runAutosave();
  } catch (e) {
    showOperationError(e.message || 'Add layer failed', e.stack || e.message, addLayer);
  } finally {
    layerApplyBtn.disabled = false;
    if (layerLoading) layerLoading.hidden = true;
  }
}

if (layerAddBtn) layerAddBtn.addEventListener('click', () => layerFileInput?.click());
if (layerFileInput) {
  layerFileInput.addEventListener('change', () => {
    if (layerFileInput.files?.length) showLayerForm(true);
  });
}
if (layerMixMode) {
  layerMixMode.addEventListener('change', () => {
    if (layerReplaceTimes) layerReplaceTimes.hidden = layerMixMode.value !== 'replace';
  });
}
if (layerApplyBtn) layerApplyBtn.addEventListener('click', addLayer);

/** Step 15: Add Cached Voice to Song */
function showCachedVoiceForm(show) {
  if (cachedVoiceForm) cachedVoiceForm.hidden = !show;
  if (cachedVoiceLoading) cachedVoiceLoading.hidden = true;
  if (show) populateCachedVoiceSelect();
}

async function populateCachedVoiceSelect() {
  if (!cachedVoiceSelect) return;
  cachedVoiceSelect.innerHTML = '<option value="">Loading…</option>';
  try {
    const res = await fetch('/api/voice/cached');
    const data = await res.json().catch(() => ({}));
    const voices = data.voices || [];
    cachedVoiceSelect.innerHTML = voices.length
      ? voices.map((v) => `<option value="${escapeHtml(v.path)}">${escapeHtml(v.name)}</option>`).join('')
      : '<option value="">No cached voices</option>';
  } catch {
    cachedVoiceSelect.innerHTML = '<option value="">Failed to load</option>';
  }
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

async function addCachedVoice() {
  const voicePath = cachedVoiceSelect?.value?.trim();
  if (!voicePath) {
    showToast('Select a cached voice');
    return;
  }
  if (!lastValidatedPath) {
    showToast('Load a song in Studio first');
    return;
  }
  if (cachedVoiceApplyBtn) cachedVoiceApplyBtn.disabled = true;
  if (cachedVoiceLoading) cachedVoiceLoading.hidden = false;
  try {
    const res = await fetch('/api/layer/add-cached-voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: lastValidatedPath,
        voicePath,
        pitchFormantMatch: !!cachedVoicePitchFormant?.checked,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Add cached voice failed', data.detail, addCachedVoice);
      return;
    }
    renderDiffSummaryList(data.modifications);
    showCachedVoiceForm(false);
    showToast(data.diffSummary || 'Cached voice added');
    runAutosave();
  } catch (e) {
    showOperationError(e.message || 'Add cached voice failed', e.stack || e.message, addCachedVoice);
  } finally {
    if (cachedVoiceApplyBtn) cachedVoiceApplyBtn.disabled = false;
    if (cachedVoiceLoading) cachedVoiceLoading.hidden = true;
  }
}

if (addCachedVoiceBtn) {
  addCachedVoiceBtn.addEventListener('click', () => {
    const visible = cachedVoiceForm && !cachedVoiceForm.hidden;
    showCachedVoiceForm(!visible);
  });
}
if (cachedVoiceApplyBtn) cachedVoiceApplyBtn.addEventListener('click', addCachedVoice);

/** Step 19: Save stem to permanent sound library */
async function saveStemToLibrary() {
  if (!lastValidatedPath) {
    showToast('Load a song first');
    return;
  }
  if (saveStemBtn) saveStemBtn.disabled = true;
  try {
    const res = await fetch('/api/stem/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: lastValidatedPath, stemType: stemSelect?.value || 'other' }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Save failed', data.detail, saveStemToLibrary);
      return;
    }
    showToast('Saved to sounds library');
  } catch (e) {
    showOperationError(e.message || 'Save failed', e.stack || e.message, saveStemToLibrary);
  } finally {
    if (saveStemBtn) saveStemBtn.disabled = false;
  }
}
if (saveStemBtn) saveStemBtn.addEventListener('click', saveStemToLibrary);

/** Step 16: Project save/load/new */
function downloadVibe(blob, filename) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function saveProjectAs() {
  if (saveProjectBtn) saveProjectBtn.disabled = true;
  try {
    const res = await fetch('/api/project/state');
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Failed to get project state', data.detail, saveProjectAs);
      return;
    }
    const vibe = {
      version: data.version,
      theme: data.theme,
      activeSongPath: lastValidatedPath,
      modifications: data.modifications,
      voiceModifications: data.voiceModifications,
      songs: data.songs,
      cachedVoices: data.cachedVoices,
    };
    const blob = new Blob([JSON.stringify(vibe, null, 2)], { type: 'application/json' });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    downloadVibe(blob, `project_${stamp}.vibe`);
    try { localStorage.setItem(LAST_MANUAL_SAVE_KEY, String(Date.now())); } catch (_) {}
    projectDirty = false;
    showToast('Project saved');
  } catch (e) {
    showOperationError(e.message || 'Save project failed', e.stack || e.message, saveProjectAs);
  } finally {
    if (saveProjectBtn) saveProjectBtn.disabled = false;
  }
}

async function loadProjectFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const vibe = JSON.parse(reader.result);
        if (vibe.version == null) reject(new Error('Invalid .vibe file'));
        resolve(vibe);
      } catch (e) {
        reject(e);
      }
    };
    reader.onerror = () => reject(new Error('Could not read file'));
    reader.readAsText(file);
  });
}

async function loadProject() {
  const file = loadProjectInput?.files?.[0];
  if (!file) return;
  if (loadProjectBtn) loadProjectBtn.disabled = true;
  try {
    const vibe = await loadProjectFromFile(file);
    const res = await fetch('/api/project/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        modifications: vibe.modifications,
        voiceModifications: vibe.voiceModifications,
        theme: vibe.theme,
        activeSongPath: vibe.activeSongPath,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'Load project failed', data.detail, () => loadProjectInput?.click());
      return;
    }
    sessionSongs = Array.isArray(vibe.songs) ? vibe.songs.map((s) => ({
      path: s.path,
      name: s.name != null ? s.name : s.path,
      duration: s.duration != null ? s.duration : null,
    })) : [];
    lastValidatedPath = data.activeSongPath ?? null;
    refreshSessionDropdown();
    loadThemeSettings();
    if (data.activeSongPath && data.activeSong) {
      loadedState.hidden = false;
      if (loadingState) loadingState.hidden = true;
      if (errorState) errorState.hidden = true;
      const dur = data.activeSong.duration != null ? formatDuration(data.activeSong.duration) : '—';
      if (loadedInfo) loadedInfo.textContent = `${data.activeSong.name} – ${dur}`;
      if (analysisPlaceholder) analysisPlaceholder.hidden = true;
    } else if (sessionSongs.length > 0 && lastValidatedPath) {
      const entry = sessionSongs.find((s) => s.path === lastValidatedPath);
      if (entry) {
        loadedState.hidden = false;
        if (loadingState) loadingState.hidden = true;
        if (errorState) errorState.hidden = true;
        if (loadedInfo) loadedInfo.textContent = `${entry.name} – ${entry.duration != null ? formatDuration(entry.duration) : '—'}`;
        if (analysisPlaceholder) analysisPlaceholder.hidden = true;
      } else {
        showSection('');
      }
    } else {
      showSection('');
    }
    await fetchVersions();
    projectDirty = false;
    showToast('Project loaded');
  } catch (e) {
    showOperationError(e.message || 'Load project failed', e.stack || e.message, () => loadProjectInput?.click());
  } finally {
    loadProjectInput.value = '';
    if (loadProjectBtn) loadProjectBtn.disabled = false;
  }
}

async function newProject() {
  if (newProjectBtn) newProjectBtn.disabled = true;
  try {
    const res = await fetch('/api/project/new', { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showOperationError(data.error || 'New project failed', data.detail, newProject);
      return;
    }
    sessionSongs = [];
    lastValidatedPath = null;
    lastVoicePath = null;
    lastVoiceExportUrl = null;
    lastExportDownloadUrl = null;
    lastExportFilename = null;
    refreshSessionDropdown();
    showSection('');
    showErrorBanner(false);
    renderDiffSummaryList([]);
    if (analysisPanel) analysisPanel.hidden = true;
    if (analysisOutput) analysisOutput.value = '';
    if (analyzeBtn) analyzeBtn.hidden = false;
    if (voiceLoadedState) voiceLoadedState.hidden = true;
    if (voiceAnalysisPlaceholder) voiceAnalysisPlaceholder.hidden = false;
    if (voiceLoadedInfo) voiceLoadedInfo.textContent = '';
    loadThemeSettings();
    projectDirty = false;
    showToast('New project started');
  } catch (e) {
    showOperationError(e.message || 'New project failed', e.stack || e.message, newProject);
  } finally {
    if (newProjectBtn) newProjectBtn.disabled = false;
  }
}

if (saveProjectBtn) saveProjectBtn.addEventListener('click', saveProjectAs);
if (loadProjectBtn) loadProjectBtn.addEventListener('click', () => loadProjectInput?.click());
if (loadProjectInput) loadProjectInput.addEventListener('change', () => { if (loadProjectInput.files?.length) loadProject(); });
if (newProjectBtn) newProjectBtn.addEventListener('click', newProject);

/* ========== Steps 24–26: After project save/load ========== */
/** Step 25: Autosave and recover session */
async function runAutosave() {
  if (!lastValidatedPath) return;
  try {
    await fetch('/api/autosave', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activeSongPath: lastValidatedPath }),
    });
  } catch (_) {}
}

async function checkRecoverSession() {
  try {
    const res = await fetch('/api/autosave/check');
    const data = await res.json().catch(() => ({}));
    if (!data.exists || data.mtime == null) {
      setTimeout(startTourIfFirstLaunch, 400);
      return;
    }
    let lastManual = null;
    try {
      const s = localStorage.getItem(LAST_MANUAL_SAVE_KEY);
      if (s) lastManual = parseInt(s, 10);
    } catch (_) {}
    if (lastManual != null && data.mtime <= lastManual) {
      setTimeout(startTourIfFirstLaunch, 400);
      return;
    }
    if (recoverSessionModal) recoverSessionModal.hidden = false;
  } catch (_) {
    setTimeout(startTourIfFirstLaunch, 400);
  }
}

async function recoverSessionLoad() {
  if (!recoverSessionModal) return;
  recoverSessionModal.hidden = true;
  try {
    const res = await fetch('/api/autosave/content');
    const vibe = await res.json().catch(() => ({}));
    if (!res.ok || !vibe.version) {
      showToast('Could not load autosave');
      return;
    }
    const loadRes = await fetch('/api/project/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        modifications: vibe.modifications,
        voiceModifications: vibe.voiceModifications,
        theme: vibe.theme,
        activeSongPath: vibe.activeSongPath,
      }),
    });
    const loadData = await loadRes.json().catch(() => ({}));
    if (!loadRes.ok) {
      showToast(loadData.error || 'Recovery failed');
      return;
    }
    sessionSongs = Array.isArray(vibe.songs) ? vibe.songs.map((s) => ({
      path: s.path,
      name: s.name != null ? s.name : s.path,
      duration: s.duration != null ? s.duration : null,
    })) : [];
    lastValidatedPath = loadData.activeSongPath ?? null;
    refreshSessionDropdown();
    loadThemeSettings();
    if (loadData.activeSongPath && loadData.activeSong) {
      loadedState.hidden = false;
      if (loadingState) loadingState.hidden = true;
      if (errorState) errorState.hidden = true;
      const dur = loadData.activeSong.duration != null ? formatDuration(loadData.activeSong.duration) : '—';
      if (loadedInfo) loadedInfo.textContent = `${loadData.activeSong.name} – ${dur}`;
      if (analysisPlaceholder) analysisPlaceholder.hidden = true;
    } else if (sessionSongs.length > 0 && lastValidatedPath) {
      const entry = sessionSongs.find((s) => s.path === lastValidatedPath);
      if (entry) {
        loadedState.hidden = false;
        if (loadingState) loadingState.hidden = true;
        if (errorState) errorState.hidden = true;
        if (loadedInfo) loadedInfo.textContent = `${entry.name} – ${entry.duration != null ? formatDuration(entry.duration) : '—'}`;
        if (analysisPlaceholder) analysisPlaceholder.hidden = true;
      } else {
        showSection('');
      }
    } else {
      showSection('');
    }
    await fetchVersions();
    projectDirty = false;
    showToast('Session recovered');
  } catch (e) {
    showToast(e.message || 'Recovery failed');
  }
  startTourIfFirstLaunch();
}

window.__checkRecoverSession = checkRecoverSession;

if (recoverSessionYes) recoverSessionYes.addEventListener('click', recoverSessionLoad);
if (recoverSessionNo) {
  recoverSessionNo.addEventListener('click', () => {
    if (recoverSessionModal) recoverSessionModal.hidden = true;
    startTourIfFirstLaunch();
  });
}

setInterval(runAutosave, AUTOSAVE_INTERVAL_MS);

/** Step 26: Minimum system requirements — show friendly warning if RAM < 4 GB free */
async function checkSystemRequirements() {
  try {
    const res = await fetch('/api/system/check');
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ramOk !== false) return;
    const freeRamGB = data.freeRamGB;
    if (freeRamGB != null && freeRamGB < MIN_FREE_RAM_GB && systemRequirementsWarning && systemRequirementsWarningText) {
      const isMac = (data.platform || '').toLowerCase() === 'darwin';
      systemRequirementsWarningText.textContent = isMac
        ? 'Your Mac has limited RAM — analysis may be slow. Close other apps for best performance.'
        : 'Your system has limited RAM — analysis may be slow. Close other apps for best performance.';
      systemRequirementsWarning.hidden = false;
    }
  } catch (_) {}
}
window.__checkSystemRequirements = checkSystemRequirements;

if (exportAudioOnlyCheckbox) {
  exportAudioOnlyCheckbox.addEventListener('change', () => {
    if (exportFormatChoice) exportFormatChoice.hidden = !exportAudioOnlyCheckbox.checked;
    persistExportSettings();
  });
}
document.querySelectorAll('input[name="export-format"]').forEach((radio) => {
  radio.addEventListener('change', persistExportSettings);
});
if (saveFinishedBtn) saveFinishedBtn.addEventListener('click', saveFinishedProduct);
if (openInFinderBtn) openInFinderBtn.addEventListener('click', openInFinder);

/* Step 29: Quit confirmation (polish & UX) — window close and Cmd+Q */
window.addEventListener('beforeunload', (e) => {
  if (!projectDirty || allowUnload) return;
  e.preventDefault();
  e.returnValue = '';
  setTimeout(showQuitConfirmModal, 0);
});
document.addEventListener('keydown', (e) => {
  if (e.metaKey && e.key === 'q') {
    if (!projectDirty) return;
    e.preventDefault();
    showQuitConfirmModal();
  }
});
if (quitConfirmSave) quitConfirmSave.addEventListener('click', onQuitConfirmSave);
if (quitConfirmNo) quitConfirmNo.addEventListener('click', onQuitConfirmNo);
if (quitConfirmCancel) quitConfirmCancel.addEventListener('click', onQuitConfirmCancel);

/* Step 7: Tab switching (Studio, Voice, Customize) */
document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    const tabId = tab.getAttribute('data-tab');
    if (!tabId) return;
    document.querySelectorAll('.tab').forEach((t) => {
      t.classList.remove('tab--active');
      t.setAttribute('aria-selected', 'false');
    });
    tab.classList.add('tab--active');
    tab.setAttribute('aria-selected', 'true');
    document.querySelectorAll('.tab-panel').forEach((panel) => {
      const isActive = panel.id === `${tabId}-tab`;
      panel.classList.toggle('tab-panel--active', isActive);
      panel.hidden = !isActive;
    });
    if (tabId === 'customize') refreshCacheSizeDisplay();
  });
});

loadThemeSettings();

analyzeBtn.addEventListener('click', runAnalysis);
applyModifyBtn.addEventListener('click', applyModification);
undoModifyBtn.addEventListener('click', undoModification);
if (redoModifyBtn) redoModifyBtn.addEventListener('click', redoModification);
if (modifyInput) {
  modifyInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      applyModification();
    }
  });
}
