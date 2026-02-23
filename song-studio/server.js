/**
 * Song Studio - backend
 * Step 2: Validates with Python MoviePy script.
 * Step 4: After validation, cache permanently as ./cache/originals/{sha256}.mp4
 *        and ./cache/originals/{sha256}_audio.wav (48 kHz, 16-bit); index in originals_index.json.
 */

import express from 'express';
import multer from 'multer';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import crypto from 'crypto';
import os from 'os';
import { spawn } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CACHE_ROOT = path.join(__dirname, 'cache');
const CACHE_ORIGINALS = path.join(__dirname, 'cache', 'originals');
const ORIGINALS_INDEX = path.join(__dirname, 'cache', 'originals_index.json');
const MODIFICATIONS_FILE = path.join(__dirname, 'cache', 'modifications.json');
const VALIDATE_SCRIPT = path.join(__dirname, 'scripts', 'validate_recording.py');
const ANALYZE_SCRIPT = path.join(__dirname, 'scripts', 'analyze_song_parts.py');
const EXTRACT_AUDIO_SCRIPT = path.join(__dirname, 'scripts', 'extract_audio.py');
const EXPORT_AUDIO_SCRIPT = path.join(__dirname, 'scripts', 'export_audio.py');
const EXPORT_VIDEO_SCRIPT = path.join(__dirname, 'scripts', 'export_video.py');
const CACHE_EXPORTS = path.join(__dirname, 'cache', 'exports');
const USER_SETTINGS_PATH = path.join(__dirname, 'cache', 'user_settings.json');
const CACHE_VOICES = path.join(__dirname, 'cache', 'voices', 'originals');
const VOICE_MODIFICATIONS_FILE = path.join(__dirname, 'cache', 'voice_modifications.json');
const CONVERT_TO_WAV_SCRIPT = path.join(__dirname, 'scripts', 'convert_to_wav.py');
const MIX_AUDIO_SCRIPT = path.join(__dirname, 'scripts', 'mix_audio.py');
const LAYER_TEMP_DIR = path.join(__dirname, 'cache', 'layers_temp');
const CACHE_VOICE_PERMANENT = path.join(__dirname, 'cache', 'voice', 'permanent');
const CACHE_SOUNDS = path.join(__dirname, 'cache', 'sounds');
const CHECK_DEPS_SCRIPT = path.join(__dirname, 'scripts', 'check_deps.py');
const CACHE_LOGS = path.join(__dirname, 'cache', 'logs');
const ERROR_LOG_PATH = path.join(CACHE_LOGS, 'errors.log');
const CACHE_AUTOSAVE = path.join(__dirname, 'cache', 'autosave');
const AUTOSAVE_FILE = path.join(CACHE_AUTOSAVE, 'latest.vibe');

// Step 21: Log errors with timestamp for debugging
function logError(context, err) {
  try {
    if (!fs.existsSync(CACHE_LOGS)) fs.mkdirSync(CACHE_LOGS, { recursive: true });
    const ts = new Date().toISOString();
    const msg = (err && err.message) ? err.message : String(err);
    const detail = (err && err.stack) ? err.stack : msg;
    const block = `[${ts}] ${context}\n${msg}\n${detail}\n---\n`;
    fs.appendFileSync(ERROR_LOG_PATH, block, 'utf8');
  } catch (_) {}
}

// Step 5: approximate section ranges as % of duration (intro 0–8%, verse 8–35%, chorus 35–65%, bridge 65–82%, outro 82–100%)
const SECTION_PCTS = { intro: [0, 0.08], verse: [0.08, 0.35], chorus: [0.35, 0.65], bridge: [0.65, 0.82], outro: [0.82, 1] };

function secToMmss(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function getSectionTimeRange(section, durationSec) {
  const pct = SECTION_PCTS[section];
  if (!pct || !durationSec) return '0:00–0:45';
  const start = pct[0] * durationSec;
  const end = pct[1] * durationSec;
  return `${secToMmss(start)}–${secToMmss(end)}`;
}

function parseModificationIntent(text) {
  const t = (text || '').toLowerCase().trim();
  const parsed = { target: null, section: null, type: null, amount: null, preserve: null };

  const stemPatterns = [
    { key: 'bass', re: /\bbass\b/ },
    { key: 'drums', re: /\b(drums?|percussion)\b/ },
    { key: 'vocals', re: /\b(vocals?|vocal)\b/ },
    { key: 'harmonic', re: /\b(harmonic|harmonics)\b/ },
    { key: 'pads', re: /\bpads?\b/ },
    { key: 'keys', re: /\b(keys?|melody|synth)\b/ },
  ];
  for (const { key, re } of stemPatterns) {
    if (re.test(t)) { parsed.target = key; break; }
  }

  const sectionPatterns = [
    { key: 'intro', re: /\bintro\b/ },
    { key: 'verse', re: /\bverse\b/ },
    { key: 'chorus', re: /\bchorus\b/ },
    { key: 'bridge', re: /\bbridge\b/ },
    { key: 'outro', re: /\boutro\b/ },
  ];
  for (const { key, re } of sectionPatterns) {
    if (re.test(t)) { parsed.section = key; break; }
  }

  if (/\b(pitch|semitones?|deeper|higher|lower|raise|shift)\b/.test(t)) parsed.type = 'pitch';
  else if (/\b(tempo|bpm|speed)\b/.test(t)) parsed.type = 'tempo';
  else if (/\b(volume|louder|quieter|softer)\b/.test(t)) parsed.type = 'volume';
  else if (/\breverb\b/.test(t)) parsed.type = 'reverb';
  else if (/\b(eq|eq'd|brighter|darker|deeper)\b/.test(t) || (parsed.target === 'bass' && /deeper/.test(t))) parsed.type = parsed.type || 'eq';
  else if (/\b(distortion|distort)\b/.test(t)) parsed.type = 'distortion';

  const semitoneMatch = t.match(/([+-]?\d+)\s*semitone|(\d+)\s*semitone|raise.*?(\d+)|(\d+).*?semitones?/i);
  if (semitoneMatch) {
    const n = parseInt(semitoneMatch[1] || semitoneMatch[2] || semitoneMatch[3] || semitoneMatch[4], 10);
    parsed.amount = (t.includes('lower') || t.includes('down') || (semitoneMatch[1] && semitoneMatch[1].startsWith('-'))) ? -n : n;
  } else if (/\bsubtle\b/.test(t)) parsed.amount = 'subtle';
  else if (/\bslight\b/.test(t)) parsed.amount = 'slight';
  else if (/\b(raise|higher|up)\b/.test(t)) parsed.amount = parsed.amount ?? 'up';
  else if (/\b(lower|deeper|down)\b/.test(t)) parsed.amount = parsed.amount ?? 'down';

  if (/\b(keep|preserve|maintain)\s+(vibe|essence|groove|feel)\b/.test(t)) parsed.preserve = true;

  return parsed;
}

function buildDiffSummary(parsed, timeRange) {
  const target = parsed.target || 'mix';
  const section = parsed.section ? ` in ${parsed.section} (${timeRange})` : '';
  const parts = [];
  if (parsed.type === 'pitch') {
    const amt = typeof parsed.amount === 'number' ? `${parsed.amount > 0 ? '+' : ''}${parsed.amount} semitones` : (parsed.amount || 'shifted');
    parts.push(`${target} pitch ${amt}${section}`);
  } else if (parsed.type === 'volume') {
    parts.push(`${target} volume ${parsed.amount === 'subtle' ? 'slightly ' : ''}${parsed.amount || 'adjusted'}${section}`);
  } else if (parsed.type === 'reverb') {
    parts.push(`${parsed.amount === 'subtle' ? 'Subtle ' : ''}reverb on ${target}${section}`);
  } else if (parsed.type === 'eq') {
    parts.push(`${target} EQ ${parsed.amount || 'adjusted'} (e.g. deeper/brighter)${section}`);
  } else if (parsed.type === 'distortion') {
    parts.push(`distortion on ${target}${section}`);
  } else if (parsed.type === 'tempo') {
    parts.push(`${target} tempo ${parsed.amount || 'adjusted'}${section}`);
  } else {
    parts.push(`${target} modified${section}`);
  }
  if (parsed.preserve) parts[parts.length - 1] += '; vibe preserved';
  return parts.join('. ');
}

function readModifications() {
  try {
    const raw = fs.readFileSync(MODIFICATIONS_FILE, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function writeModifications(obj) {
  fs.writeFileSync(MODIFICATIONS_FILE, JSON.stringify(obj, null, 2), 'utf8');
}

function readVoiceModifications() {
  try {
    const raw = fs.readFileSync(VOICE_MODIFICATIONS_FILE, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function writeVoiceModifications(obj) {
  fs.writeFileSync(VOICE_MODIFICATIONS_FILE, JSON.stringify(obj, null, 2), 'utf8');
}

function readUserSettings() {
  try {
    const raw = fs.readFileSync(USER_SETTINGS_PATH, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function writeUserSettings(obj) {
  const dir = path.dirname(USER_SETTINGS_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(USER_SETTINGS_PATH, JSON.stringify(obj, null, 2), 'utf8');
}

// Step 13: Phonetically balanced phrase sets per language (4–8 sentences for voice cloning)
const VOICE_PHRASES = {
  en: {
    name: 'English',
    phrases: [
      'The birch canoe slid on the smooth planks.',
      'Glue the sheet to the dark blue background.',
      'It\'s easy to tell the depth of a well.',
      'These days a chicken leg is a rare dish.',
      'Rice is often served in round bowls.',
      'The juice of lemons makes fine punch.',
      'The box was thrown beside the parked truck.',
      'The hogs were fed chopped corn and garbage.',
    ],
  },
  es: {
    name: 'Spanish',
    phrases: [
      'El perro ladró al gato en el jardín.',
      'La lluvia cae suave sobre el tejado.',
      'El niño leyó un libro bajo la luz.',
      'Las flores crecen en el campo verde.',
      'El pan recién hecho huele muy bien.',
      'La música suena fuerte en la sala.',
      'El sol brilla sobre la playa blanca.',
      'La noche es tranquila en la ciudad.',
    ],
  },
  ja: {
    name: 'Japanese',
    phrases: [
      '桜の花が散る季節が来た。',
      '彼は毎朝早く起きる。',
      'この本はとても面白い。',
      '雨の日は家で過ごす。',
      '新しい車を買った。',
      '明日は晴れるでしょう。',
      '日本語を勉強しています。',
      '友達と一緒に食事した。',
    ],
  },
  ru: {
    name: 'Russian',
    phrases: [
      'Собака лает на кошку в саду.',
      'Дождь идёт над городом вечером.',
      'Ребёнок читает книгу при свете.',
      'Цветы растут в зелёном поле.',
      'Свежий хлеб пахнет очень хорошо.',
      'Музыка звучит громко в зале.',
      'Солнце светит над белым пляжем.',
      'Ночью в городе тихо и спокойно.',
    ],
  },
};

const VOICE_PHRASES_FALLBACK = 'Unsupported language – use English phrases as a base and speak in your target language.';

function normalizeLanguageCode(input) {
  if (!input || typeof input !== 'string') return null;
  const t = input.trim().toLowerCase();
  if (/^(english|en)$/.test(t)) return 'en';
  if (/^(spanish|español|es)$/.test(t)) return 'es';
  if (/^(japanese|日本語|ja)$/.test(t)) return 'ja';
  if (/^(russian|русский|ru)$/.test(t)) return 'ru';
  return null;
}

if (!fs.existsSync(CACHE_ORIGINALS)) {
  fs.mkdirSync(CACHE_ORIGINALS, { recursive: true });
}
if (!fs.existsSync(CACHE_EXPORTS)) {
  fs.mkdirSync(CACHE_EXPORTS, { recursive: true });
}
if (!fs.existsSync(CACHE_VOICES)) {
  fs.mkdirSync(CACHE_VOICES, { recursive: true });
}
if (!fs.existsSync(LAYER_TEMP_DIR)) {
  fs.mkdirSync(LAYER_TEMP_DIR, { recursive: true });
}
if (!fs.existsSync(CACHE_VOICE_PERMANENT)) {
  fs.mkdirSync(CACHE_VOICE_PERMANENT, { recursive: true });
}
if (!fs.existsSync(CACHE_SOUNDS)) {
  fs.mkdirSync(CACHE_SOUNDS, { recursive: true });
}
if (!fs.existsSync(CACHE_AUTOSAVE)) {
  fs.mkdirSync(CACHE_AUTOSAVE, { recursive: true });
}

function computeFileHash(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('data', (d) => hash.update(d));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

function runExtractAudio(videoPath, wavPath) {
  return new Promise((resolve) => {
    const py = spawn('python3', [EXTRACT_AUDIO_SCRIPT, videoPath, wavPath], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let stderr = '';
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => {
      resolve(code === 0 ? null : stderr || 'Extract failed');
    });
    py.on('error', (err) => resolve(err.message || 'Could not run extract'));
  });
}

function runExportAudio(wavPath, outPath, format) {
  if (format === 'wav') {
    try {
      fs.copyFileSync(wavPath, outPath);
      return Promise.resolve(null);
    } catch (e) {
      return Promise.resolve(e.message || 'Copy failed');
    }
  }
  return new Promise((resolve) => {
    const py = spawn('python3', [EXPORT_AUDIO_SCRIPT, wavPath, outPath], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let stderr = '';
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => resolve(code === 0 ? null : stderr || 'Export failed'));
    py.on('error', (err) => resolve(err.message || 'Could not run export'));
  });
}

function runExportVideo(videoPath, audioPath, outPath) {
  return new Promise((resolve) => {
    const py = spawn('python3', [EXPORT_VIDEO_SCRIPT, videoPath, audioPath, outPath], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let stderr = '';
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => resolve(code === 0 ? null : stderr || 'Export failed'));
    py.on('error', (err) => resolve(err.message || 'Could not run export'));
  });
}

function runConvertToWav(inputPath, outputPath) {
  return new Promise((resolve) => {
    const py = spawn('python3', [CONVERT_TO_WAV_SCRIPT, inputPath, outputPath], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    let stderr = '';
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => resolve(code === 0 ? null : stderr || 'Convert failed'));
    py.on('error', (err) => resolve(err.message || 'Could not run convert'));
  });
}

function runMixAudio(mainWav, layerWav, outWav, mode, startSec, endSec) {
  return new Promise((resolve) => {
    const args = [MIX_AUDIO_SCRIPT, mainWav, layerWav, outWav, mode];
    if (mode === 'replace' && startSec != null && endSec != null) {
      args.push(String(startSec), String(endSec));
    }
    const py = spawn('python3', args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = '';
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => resolve(code === 0 ? null : stderr || 'Mix failed'));
    py.on('error', (err) => resolve(err.message || 'Could not run mix'));
  });
}

function readOriginalsIndex() {
  try {
    const raw = fs.readFileSync(ORIGINALS_INDEX, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function writeOriginalsIndex(obj) {
  fs.writeFileSync(ORIGINALS_INDEX, JSON.stringify(obj, null, 2), 'utf8');
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, CACHE_ORIGINALS),
  filename: (_req, file, cb) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const safe = (file.originalname || 'recording').replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `${timestamp}_${safe}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 1024 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname || '').toLowerCase();
    const allowed = ['.mp4', '.mov', '.mkv', '.avi'];
    if (allowed.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error(`Unsupported format. Use: ${allowed.join(', ')}`));
    }
  },
});

const voiceStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, CACHE_VOICES),
  filename: (_req, file, cb) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const safe = (file.originalname || 'voice').replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `${timestamp}_${safe}`);
  },
});

const voiceUpload = multer({
  storage: voiceStorage,
  limits: { fileSize: 300 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname || '').toLowerCase();
    const allowed = ['.wav', '.mp3', '.m4a', '.ogg', '.mp4', '.mov'];
    if (allowed.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Voice: use .wav, .mp3, .m4a, .ogg, or .mp4'));
    }
  },
});

const layerStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, LAYER_TEMP_DIR),
  filename: (_req, file, cb) => {
    const t = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const safe = (file.originalname || 'layer').replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `layer_${t}_${safe}`);
  },
});

const layerUpload = multer({
  storage: layerStorage,
  limits: { fileSize: 500 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname || '').toLowerCase();
    const allowed = ['.wav', '.mp3', '.m4a', '.ogg', '.mp4', '.mov', '.mkv', '.avi'];
    if (allowed.includes(ext)) cb(null, true);
    else cb(new Error('Layer: use .wav, .mp3, .m4a, .ogg, .mp4, .mov, .mkv, .avi'));
  },
});

const app = express();
app.use(express.json());

// Step 20: Setup check (before static so API is available)
app.get('/api/setup/check', async (_req, res) => {
  let pythonOk = false;
  let missing = [];
  try {
    const pyResult = await new Promise((resolve) => {
      const py = spawn('python3', [CHECK_DEPS_SCRIPT], {
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      let stdout = '';
      let stderr = '';
      py.stdout.on('data', (d) => { stdout += d; });
      py.stderr.on('data', (d) => { stderr += d; });
      py.on('close', (code) => resolve({ code, stdout, stderr }));
      py.on('error', () => resolve({ code: -1, stdout: '', stderr: 'Could not run python3' }));
    });
    const data = JSON.parse(pyResult.stdout.trim() || '{"missing":[]}');
    missing = Array.isArray(data.missing) ? data.missing : [];
    pythonOk = missing.length === 0;
  } catch (e) {
    missing = ['torch', 'torchaudio', 'demucs', 'librosa', 'moviepy', 'pydub', 'ffmpeg-python', 'numpy', 'soundfile'];
  }
  let ffmpegOk = false;
  try {
    const ffResult = await new Promise((resolve) => {
      const child = spawn('ffmpeg', ['-version'], { stdio: ['ignore', 'pipe', 'pipe'] });
      child.on('close', (code) => resolve(code === 0));
      child.on('error', () => resolve(false));
    });
    ffmpegOk = !!ffResult;
  } catch {
    ffmpegOk = false;
  }
  const platform = process.platform || '';
  res.status(200).json({
    python: { ok: pythonOk, missing },
    ffmpeg: { ok: ffmpegOk },
    platform,
  });
});

// Step 23: Cache size and clear
function getDirSizeBytes(dirPath) {
  if (!fs.existsSync(dirPath)) return 0;
  let total = 0;
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    for (const e of entries) {
      const full = path.join(dirPath, e.name);
      if (e.isDirectory()) {
        total += getDirSizeBytes(full);
      } else {
        try {
          total += fs.statSync(full).size;
        } catch (_) {}
      }
    }
  } catch (_) {}
  return total;
}

function getCacheSizeBytes() {
  return getDirSizeBytes(CACHE_ROOT);
}

app.get('/api/cache/size', (_req, res) => {
  try {
    const bytes = getCacheSizeBytes();
    res.status(200).json({ bytes, bytesFormatted: formatBytes(bytes) });
  } catch (e) {
    logError('cache/size', e);
    res.status(500).json({ error: e.message || 'Failed to get cache size', bytes: 0, bytesFormatted: '0 B' });
  }
});

function formatBytes(n) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} MB`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} KB`;
  return `${n} B`;
}

function clearDirContents(dirPath) {
  if (!fs.existsSync(dirPath)) return;
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dirPath, e.name);
    if (e.isDirectory()) {
      clearDirContents(full);
      fs.rmdirSync(full);
    } else {
      try { fs.unlinkSync(full); } catch (_) {}
    }
  }
}

function clearOriginalsMixedOnly() {
  if (!fs.existsSync(CACHE_ORIGINALS)) return;
  const entries = fs.readdirSync(CACHE_ORIGINALS);
  for (const name of entries) {
    if (name.endsWith('_mixed.wav')) {
      try { fs.unlinkSync(path.join(CACHE_ORIGINALS, name)); } catch (_) {}
    }
  }
}

app.post('/api/cache/clear', express.json(), (req, res) => {
  const mode = (req.body?.mode || '').toLowerCase();
  const valid = ['all', 'old_versions', 'keep_originals'];
  if (!valid.includes(mode)) {
    return res.status(400).json({ error: 'Invalid mode. Use: all, old_versions, keep_originals' });
  }
  try {
    if (mode === 'all') {
      clearDirContents(CACHE_ORIGINALS);
      clearDirContents(CACHE_EXPORTS);
      clearDirContents(CACHE_VOICES);
      clearDirContents(CACHE_VOICE_PERMANENT);
      clearDirContents(CACHE_SOUNDS);
      clearDirContents(LAYER_TEMP_DIR);
      clearDirContents(CACHE_LOGS);
      writeOriginalsIndex({});
      writeModifications({});
      writeVoiceModifications({});
    } else if (mode === 'old_versions') {
      clearDirContents(CACHE_EXPORTS);
      clearDirContents(LAYER_TEMP_DIR);
      clearOriginalsMixedOnly();
      writeModifications({});
      writeVoiceModifications({});
    } else {
      // keep_originals: remove everything except originals (mp4 + _audio.wav)
      clearDirContents(CACHE_EXPORTS);
      clearDirContents(CACHE_VOICES);
      clearDirContents(CACHE_VOICE_PERMANENT);
      clearDirContents(CACHE_SOUNDS);
      clearDirContents(LAYER_TEMP_DIR);
      clearDirContents(CACHE_LOGS);
      clearOriginalsMixedOnly();
      writeModifications({});
      writeVoiceModifications({});
      // originals_index stays so we keep track of what's there
    }
    const bytes = getCacheSizeBytes();
    res.status(200).json({ ok: true, bytes, bytesFormatted: formatBytes(bytes) });
  } catch (e) {
    logError('cache/clear', e);
    res.status(500).json({ error: e.message || 'Clear failed' });
  }
});

// Step 26: Minimum system requirements (RAM ≥4 GB free, CPU cores, GPU/CUDA)
const MIN_FREE_RAM_GB = 4;
app.get('/api/system/check', async (_req, res) => {
  try {
    const freeBytes = os.freemem();
    const totalBytes = os.totalmem();
    const freeRamGB = Math.round((freeBytes / 1e9) * 10) / 10;
    const totalRamGB = Math.round((totalBytes / 1e9) * 10) / 10;
    const cpuCores = os.cpus().length;
    const platform = process.platform || '';
    let cudaAvailable = false;
    try {
      const result = await new Promise((resolve) => {
        const py = spawn('python3', ['-c', 'import torch; print(torch.cuda.is_available())'], {
          stdio: ['ignore', 'pipe', 'pipe'],
        });
        let out = '';
        py.stdout.on('data', (d) => { out += d; });
        py.on('close', (code) => resolve(code === 0 ? out.trim() : ''));
        py.on('error', () => resolve(''));
      });
      cudaAvailable = result === 'True';
    } catch (_) {
      cudaAvailable = false;
    }
    res.status(200).json({
      freeRamGB,
      totalRamGB,
      cpuCores,
      cudaAvailable,
      platform,
      ramOk: freeRamGB >= MIN_FREE_RAM_GB,
    });
  } catch (e) {
    logError('system/check', e);
    res.status(500).json({
      freeRamGB: null,
      totalRamGB: null,
      cpuCores: null,
      cudaAvailable: false,
      platform: process.platform || '',
      ramOk: true,
    });
  }
});

app.use(express.static(path.join(__dirname, 'public')));

/** Step 2/9: File corruption checks. Use for every file upload (video, audio, voice, layers). */
function runValidation(absolutePath) {
  return new Promise((resolve) => {
    const py = spawn('python3', [VALIDATE_SCRIPT, absolutePath], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    py.stdout.on('data', (d) => { stdout += d; });
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', (code) => {
      try {
        const out = JSON.parse(stdout.trim());
        resolve(out);
      } catch {
        resolve({ ok: false, error: stderr || stdout || 'Validation script failed' });
      }
    });
    py.on('error', (err) => {
      resolve({ ok: false, error: err.message || 'Could not run validator' });
    });
  });
}

function runAnalysis(absolutePath) {
  return new Promise((resolve) => {
    const py = spawn('python3', [ANALYZE_SCRIPT, absolutePath], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    py.stdout.on('data', (d) => { stdout += d; });
    py.stderr.on('data', (d) => { stderr += d; });
    py.on('close', () => {
      try {
        const out = JSON.parse(stdout.trim());
        resolve(out);
      } catch {
        resolve({ error: stderr || stdout || 'Analysis failed' });
      }
    });
    py.on('error', (err) => {
      resolve({ error: err.message || 'Could not run analysis' });
    });
  });
}

app.get('/api/settings', (_req, res) => {
  const settings = readUserSettings();
  res.status(200).json(settings);
});

app.post('/api/settings', express.json(), (req, res) => {
  const theme = req.body?.theme;
  if (theme != null && typeof theme !== 'string') {
    return res.status(400).json({ error: 'Invalid theme' });
  }
  const exportAudioOnly = req.body?.exportAudioOnly;
  const exportFormat = req.body?.exportFormat;
  if (exportAudioOnly != null && typeof exportAudioOnly !== 'boolean') {
    return res.status(400).json({ error: 'Invalid exportAudioOnly' });
  }
  if (exportFormat != null && exportFormat !== 'mp3' && exportFormat !== 'wav') {
    return res.status(400).json({ error: 'Invalid exportFormat' });
  }
  const settings = readUserSettings();
  if (theme != null) settings.theme = theme;
  if (exportAudioOnly != null) settings.exportAudioOnly = exportAudioOnly;
  if (exportFormat != null) settings.exportFormat = exportFormat;
  writeUserSettings(settings);
  res.status(200).json(settings);
});

app.get('/api/voice/phrases', (req, res) => {
  const lang = req.query?.lang;
  const code = normalizeLanguageCode(lang || '');
  if (code && VOICE_PHRASES[code]) {
    const data = VOICE_PHRASES[code];
    return res.status(200).json({
      language: data.name,
      languageCode: code,
      phrases: data.phrases,
    });
  }
  res.status(200).json({
    fallback: true,
    message: VOICE_PHRASES_FALLBACK,
    suggestedPhrases: VOICE_PHRASES.en.phrases,
  });
});

app.post('/api/voice/upload', voiceUpload.single('voice'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  const absolutePath = path.resolve(req.file.path);
  try {
    const hash = await computeFileHash(absolutePath);
    const wavFilename = `${hash}.wav`;
    const wavPath = path.join(CACHE_VOICES, wavFilename);
    const err = await runConvertToWav(absolutePath, wavPath);
    fs.unlinkSync(absolutePath);
    if (err) {
      logError('voice/upload', new Error(err));
      return res.status(500).json({ error: err, detail: err });
    }
    const relativePath = path.join('cache', 'voices', 'originals', wavFilename).replace(/\\/g, '/');
    res.status(200).json({
      path: relativePath,
      originalName: req.file.originalname || wavFilename,
    });
  } catch (e) {
    try { fs.unlinkSync(absolutePath); } catch { }
    logError('voice/upload', e);
    res.status(500).json({ error: e.message || 'Voice upload failed', detail: e.stack || e.message });
  }
});

app.get('/api/voice/versions', (req, res) => {
  const relativePath = req.query?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToVoices = path.relative(CACHE_VOICES, absolutePath);
  if (relToVoices.startsWith('..') || path.isAbsolute(relToVoices)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  const mods = readVoiceModifications();
  res.status(200).json({ modifications: mods[relativePath] || [] });
});

app.post('/api/voice/modify', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  const description = req.body?.description;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  if (!description || typeof description !== 'string') {
    return res.status(400).json({ error: 'Describe your change' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToVoices = path.relative(CACHE_VOICES, absolutePath);
  if (relToVoices.startsWith('..') || path.isAbsolute(relToVoices)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  const parsed = parseModificationIntent(description);
  const timeRange = getSectionTimeRange(parsed.section || 'intro', 120);
  const diffSummary = buildDiffSummary(parsed, timeRange);
  const modification = {
    id: `v${Date.now()}`,
    description: description.trim(),
    parsed: { target: parsed.target, section: parsed.section, type: parsed.type, amount: parsed.amount, preserve: parsed.preserve },
    diffSummary,
    createdAt: new Date().toISOString(),
  };
  try {
    const mods = readVoiceModifications();
    if (!mods[relativePath]) mods[relativePath] = [];
    mods[relativePath].push(modification);
    writeVoiceModifications(mods);
    res.status(200).json({
      versionId: modification.id,
      diffSummary: modification.diffSummary,
      modifications: mods[relativePath],
    });
  } catch (e) {
    logError('voice/modify', e);
    res.status(500).json({ error: e.message || 'Voice modification failed', detail: e.stack || e.message });
  }
});

app.post('/api/voice/undo', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToVoices = path.relative(CACHE_VOICES, absolutePath);
  if (relToVoices.startsWith('..') || path.isAbsolute(relToVoices)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  try {
    const mods = readVoiceModifications();
    const list = mods[relativePath] || [];
    if (list.length > 0) {
      list.pop();
      mods[relativePath] = list;
      writeVoiceModifications(mods);
    }
    res.status(200).json({ modifications: mods[relativePath] || [] });
  } catch (e) {
    logError('voice/undo', e);
    res.status(500).json({ error: e.message || 'Voice undo failed', detail: e.stack || e.message });
  }
});

app.post('/api/voice/export', express.json(), async (req, res) => {
  const relativePath = req.body?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToVoices = path.relative(CACHE_VOICES, absolutePath);
  if (relToVoices.startsWith('..') || path.isAbsolute(relToVoices)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'File not found' });
  }
  const baseName = sanitizeBasename(path.basename(relativePath, '.wav'));
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19).replace('T', '_');
  const exportFilename = `voice_${baseName}_${timestamp}.wav`;
  const exportPath = path.join(CACHE_EXPORTS, exportFilename);
  try {
    fs.copyFileSync(absolutePath, exportPath);
  } catch (e) {
    logError('voice/export', e);
    return res.status(500).json({ error: e.message || 'Export failed', detail: e.stack || e.message });
  }
  res.status(200).json({
    downloadUrl: `/api/export/download?file=${encodeURIComponent(exportFilename)}`,
    filename: exportFilename,
    path: `cache/exports/${exportFilename}`,
  });
});

app.get('/api/voice/cached', (_req, res) => {
  try {
    const files = fs.readdirSync(CACHE_VOICE_PERMANENT);
    const voices = files
      .filter((f) => f.endsWith('.wav'))
      .map((f) => ({
        id: f,
        name: f.replace(/\.wav$/i, ''),
        path: path.join('cache', 'voice', 'permanent', f).replace(/\\/g, '/'),
      }));
    res.status(200).json({ voices });
  } catch (e) {
    res.status(200).json({ voices: [] });
  }
});

app.post('/api/voice/cache', express.json(), (req, res) => {
  const voicePath = req.body?.path;
  const name = (req.body?.name || '').trim().replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80);
  if (!voicePath || typeof voicePath !== 'string') {
    return res.status(400).json({ error: 'Missing voice path' });
  }
  const absolutePath = path.resolve(__dirname, voicePath);
  const relToVoices = path.relative(CACHE_VOICES, absolutePath);
  if (relToVoices.startsWith('..') || path.isAbsolute(relToVoices)) {
    return res.status(400).json({ error: 'Invalid voice path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'Voice file not found' });
  }
  const base = name || new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const destName = base.endsWith('.wav') ? base : `${base}.wav`;
  const destPath = path.join(CACHE_VOICE_PERMANENT, destName);
  try {
    fs.copyFileSync(absolutePath, destPath);
  } catch (e) {
    logError('voice/cache', e);
    return res.status(500).json({ error: e.message || 'Cache failed', detail: e.stack || e.message });
  }
  const relativeDest = path.join('cache', 'voice', 'permanent', destName).replace(/\\/g, '/');
  res.status(200).json({ path: relativeDest, name: destName });
});

// Step 16: Project save/load
const VIBE_VERSION = 1;

function getCachedVoicesList() {
  try {
    const files = fs.readdirSync(CACHE_VOICE_PERMANENT);
    return files
      .filter((f) => f.endsWith('.wav'))
      .map((f) => ({
        id: f,
        name: f.replace(/\.wav$/i, ''),
        path: path.join('cache', 'voice', 'permanent', f).replace(/\\/g, '/'),
      }));
  } catch {
    return [];
  }
}

app.get('/api/project/state', (_req, res) => {
  try {
    const modifications = readModifications();
    const voiceModifications = readVoiceModifications();
    const settings = readUserSettings();
    const theme = settings.theme || 'fl_studio';
    const index = readOriginalsIndex();
    const songs = Object.entries(index).map(([filename, entry]) => ({
      path: path.join('cache', 'originals', filename).replace(/\\/g, '/'),
      name: (entry && entry.originalName) ? entry.originalName : filename,
      duration: (entry && entry.duration) != null ? entry.duration : null,
    }));
    const cachedVoices = getCachedVoicesList();
    res.status(200).json({
      version: VIBE_VERSION,
      theme,
      modifications,
      voiceModifications,
      songs,
      cachedVoices,
    });
  } catch (e) {
    logError('project/state', e);
    res.status(500).json({ error: e.message || 'Failed to read project state', detail: e.stack || e.message });
  }
});

// Step 25: Autosave — check, content, write
function buildProjectState(activeSongPath = null) {
  const modifications = readModifications();
  const voiceModifications = readVoiceModifications();
  const settings = readUserSettings();
  const theme = settings.theme || 'fl_studio';
  const index = readOriginalsIndex();
  const songs = Object.entries(index).map(([filename, entry]) => ({
    path: path.join('cache', 'originals', filename).replace(/\\/g, '/'),
    name: (entry && entry.originalName) ? entry.originalName : filename,
    duration: (entry && entry.duration) != null ? entry.duration : null,
  }));
  const cachedVoices = getCachedVoicesList();
  return {
    version: VIBE_VERSION,
    theme,
    activeSongPath: activeSongPath != null ? activeSongPath : null,
    modifications,
    voiceModifications,
    songs,
    cachedVoices,
  };
}

app.get('/api/autosave/check', (_req, res) => {
  try {
    if (!fs.existsSync(AUTOSAVE_FILE)) {
      return res.status(200).json({ exists: false, mtime: null });
    }
    const stat = fs.statSync(AUTOSAVE_FILE);
    res.status(200).json({ exists: true, mtime: stat.mtimeMs });
  } catch (e) {
    logError('autosave/check', e);
    res.status(200).json({ exists: false, mtime: null });
  }
});

app.get('/api/autosave/content', (_req, res) => {
  try {
    if (!fs.existsSync(AUTOSAVE_FILE)) {
      return res.status(404).json({ error: 'No autosave found' });
    }
    const raw = fs.readFileSync(AUTOSAVE_FILE, 'utf8');
    const vibe = JSON.parse(raw);
    res.status(200).json(vibe);
  } catch (e) {
    logError('autosave/content', e);
    res.status(500).json({ error: e.message || 'Failed to read autosave' });
  }
});

app.post('/api/autosave', express.json(), (req, res) => {
  const activeSongPath = req.body?.activeSongPath;
  try {
    const state = buildProjectState(activeSongPath != null ? activeSongPath : null);
    fs.writeFileSync(AUTOSAVE_FILE, JSON.stringify(state, null, 2), 'utf8');
    res.status(200).json({ ok: true });
  } catch (e) {
    logError('autosave/write', e);
    res.status(500).json({ error: e.message || 'Autosave failed' });
  }
});

app.post('/api/project/load', express.json(), (req, res) => {
  const body = req.body || {};
  const modifications = body.modifications;
  const voiceModifications = body.voiceModifications;
  const theme = body.theme;
  const activeSongPath = body.activeSongPath;

  if (modifications != null && typeof modifications !== 'object') {
    return res.status(400).json({ error: 'Invalid modifications' });
  }
  if (voiceModifications != null && typeof voiceModifications !== 'object') {
    return res.status(400).json({ error: 'Invalid voiceModifications' });
  }
  try {
    if (modifications != null) writeModifications(modifications);
    if (voiceModifications != null) writeVoiceModifications(voiceModifications);
    if (theme != null && typeof theme === 'string') {
      const settings = readUserSettings();
      settings.theme = theme;
      writeUserSettings(settings);
    }
    let activeSong = null;
    if (activeSongPath != null && typeof activeSongPath === 'string') {
      const filename = path.basename(activeSongPath);
      const index = readOriginalsIndex();
      const entry = index[filename];
      if (entry) {
        activeSong = {
          name: entry.originalName || filename,
          duration: entry.duration,
        };
      }
    }
    res.status(200).json({
      activeSongPath: activeSongPath != null && typeof activeSongPath === 'string' ? activeSongPath : null,
      activeSong,
    });
  } catch (e) {
    logError('project/load', e);
    res.status(500).json({ error: e.message || 'Failed to load project', detail: e.stack || e.message });
  }
});

app.post('/api/project/new', (_req, res) => {
  try {
    writeModifications({});
    writeVoiceModifications({});
    const settings = readUserSettings();
    settings.theme = 'fl_studio';
    writeUserSettings(settings);
    res.status(200).json({ ok: true });
  } catch (e) {
    logError('project/new', e);
    res.status(500).json({ error: e.message || 'Failed to reset project', detail: e.stack || e.message });
  }
});

// Step 19: Save stem to permanent sound library
const STEM_TYPES = ['drums', 'bass', 'vocals', 'other'];
app.post('/api/stem/save', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  const stemType = (req.body?.stemType || '').toLowerCase();
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing song path' });
  }
  if (!STEM_TYPES.includes(stemType)) {
    return res.status(400).json({ error: 'Invalid stem type. Use: drums, bass, vocals, other' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid song path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'Song file not found' });
  }
  const filename = path.basename(absolutePath);
  const hash = filename.replace(/\.mp4$/i, '');
  const mainAudioPath = path.join(CACHE_ORIGINALS, `${hash}_audio.wav`);
  const mixedPath = path.join(CACHE_ORIGINALS, `${hash}_mixed.wav`);
  const sourcePath = fs.existsSync(mixedPath) ? mixedPath : mainAudioPath;
  if (!fs.existsSync(sourcePath)) {
    return res.status(400).json({ error: 'Song audio not found' });
  }
  const songName = path.basename(relativePath, '.mp4').replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80) || 'song';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const destName = `${stemType}_${songName}_${timestamp}.wav`;
  const destPath = path.join(CACHE_SOUNDS, destName);
  try {
    fs.copyFileSync(sourcePath, destPath);
  } catch (e) {
    logError('stem/save', e);
    return res.status(500).json({ error: e.message || 'Save failed', detail: e.stack || e.message });
  }
  res.status(200).json({ ok: true, path: `cache/sounds/${destName}` });
});

const LAYER_MODE_LABELS = {
  overlay50: 'Overlay at 50% volume',
  replace: 'Replace section',
  append: 'Append',
  sidechain: 'Sidechain ducking',
};

app.post('/api/layer/add', layerUpload.single('layer'), async (req, res) => {
  const relativePath = (req.body && req.body.path) || '';
  const mixMode = (req.body && req.body.mixMode) || 'overlay50';
  const startTime = parseFloat(req.body && req.body.startTime);
  const endTime = parseFloat(req.body && req.body.endTime);

  if (!req.file) {
    return res.status(400).json({ error: 'No layer file uploaded' });
  }
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing song path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid song path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'Song file not found' });
  }
  const filename = path.basename(absolutePath);
  const hash = filename.replace(/\.mp4$/i, '');
  const mainAudioPath = path.join(CACHE_ORIGINALS, `${hash}_audio.wav`);
  const mixedPath = path.join(CACHE_ORIGINALS, `${hash}_mixed.wav`);
  const mainPath = fs.existsSync(mixedPath) ? mixedPath : mainAudioPath;
  if (!fs.existsSync(mainPath)) {
    return res.status(400).json({ error: 'Song audio not found' });
  }

  const layerTempPath = path.resolve(req.file.path);
  const layerWavPath = path.join(LAYER_TEMP_DIR, `layer_${Date.now()}.wav`);
  try {
    const convertErr = await runConvertToWav(layerTempPath, layerWavPath);
    fs.unlinkSync(layerTempPath);
    if (convertErr) {
      logError('layer/add', new Error(convertErr));
      return res.status(500).json({ error: convertErr, detail: convertErr });
    }
  } catch (e) {
    try { fs.unlinkSync(layerTempPath); } catch { }
    logError('layer/add', e);
    return res.status(500).json({ error: e.message || 'Layer convert failed', detail: e.stack || e.message });
  }

  const validModes = ['overlay50', 'replace', 'append', 'sidechain'];
  const mode = validModes.includes(mixMode) ? mixMode : 'overlay50';
  const startSec = Number.isFinite(startTime) ? startTime : 0;
  const endSec = Number.isFinite(endTime) ? endTime : 0;

  const mixErr = await runMixAudio(mainPath, layerWavPath, mixedPath, mode, startSec, endSec);
  try { fs.unlinkSync(layerWavPath); } catch { }
  if (mixErr) {
    logError('layer/add', new Error(mixErr));
    return res.status(500).json({ error: mixErr, detail: mixErr });
  }

  const songPath = path.join('cache', 'originals', filename).replace(/\\/g, '/');
  const mods = readModifications();
  if (!mods[songPath]) mods[songPath] = [];
  const label = LAYER_MODE_LABELS[mode] || mode;
  const modification = {
    id: `v${Date.now()}`,
    description: `Added audio/video layer: ${label}`,
    parsed: { type: 'layer', mixMode: mode, startTime: startSec, endTime: endSec },
    diffSummary: `Added layer: ${label}`,
    createdAt: new Date().toISOString(),
  };
  mods[songPath].push(modification);
  writeModifications(mods);

  res.status(200).json({
    versionId: modification.id,
    diffSummary: modification.diffSummary,
    modifications: mods[songPath],
  });
});

app.post('/api/layer/add-cached-voice', express.json(), async (req, res) => {
  const relativePath = req.body?.path;
  const voicePath = req.body?.voicePath;
  const pitchFormantMatch = !!req.body?.pitchFormantMatch;

  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing song path' });
  }
  if (!voicePath || typeof voicePath !== 'string') {
    return res.status(400).json({ error: 'Missing voice path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid song path' });
  }
  const voiceAbsolute = path.resolve(__dirname, voicePath);
  const relToPermanent = path.relative(CACHE_VOICE_PERMANENT, voiceAbsolute);
  if (relToPermanent.startsWith('..') || path.isAbsolute(relToPermanent)) {
    return res.status(400).json({ error: 'Invalid cached voice path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'Song file not found' });
  }
  if (!fs.existsSync(voiceAbsolute)) {
    return res.status(404).json({ error: 'Cached voice not found' });
  }
  const filename = path.basename(absolutePath);
  const hash = filename.replace(/\.mp4$/i, '');
  const mainAudioPath = path.join(CACHE_ORIGINALS, `${hash}_audio.wav`);
  const mixedPath = path.join(CACHE_ORIGINALS, `${hash}_mixed.wav`);
  const mainPath = fs.existsSync(mixedPath) ? mixedPath : mainAudioPath;
  if (!fs.existsSync(mainPath)) {
    return res.status(400).json({ error: 'Song audio not found' });
  }

  const mixErr = await runMixAudio(mainPath, voiceAbsolute, mixedPath, 'overlay50');
  if (mixErr) {
    logError('layer/add-cached-voice', new Error(mixErr));
    return res.status(500).json({ error: mixErr, detail: mixErr });
  }

  const songPath = path.join('cache', 'originals', filename).replace(/\\/g, '/');
  const mods = readModifications();
  if (!mods[songPath]) mods[songPath] = [];
  const label = pitchFormantMatch ? 'Cached voice (pitch/formant match requested)' : 'Cached voice';
  const modification = {
    id: `v${Date.now()}`,
    description: `Added cached voice: ${path.basename(voicePath, '.wav')}${pitchFormantMatch ? ' (pitch/formant match)' : ''}`,
    parsed: { type: 'cachedVoice', voicePath, pitchFormantMatch },
    diffSummary: label,
    createdAt: new Date().toISOString(),
  };
  mods[songPath].push(modification);
  writeModifications(mods);

  res.status(200).json({
    versionId: modification.id,
    diffSummary: modification.diffSummary,
    modifications: mods[songPath],
  });
});

app.get('/api/versions', (req, res) => {
  const relativePath = req.query?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const mods = readModifications();
  const list = mods[relativePath] || [];
  res.status(200).json({ modifications: list });
});

app.post('/api/modify', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  const description = req.body?.description;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  if (!description || typeof description !== 'string') {
    return res.status(400).json({ error: 'Describe your change' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  const filename = path.basename(absolutePath);
  const index = readOriginalsIndex();
  const entry = index[filename];
  const durationSec = entry?.duration ?? 180;

  const parsed = parseModificationIntent(description);
  const section = parsed.section || 'intro';
  const timeRange = getSectionTimeRange(section, durationSec);
  const diffSummary = buildDiffSummary(parsed, timeRange);

  const modification = {
    id: `v${Date.now()}`,
    description: description.trim(),
    parsed: { target: parsed.target, section: parsed.section, type: parsed.type, amount: parsed.amount, preserve: parsed.preserve },
    diffSummary,
    createdAt: new Date().toISOString(),
  };

  try {
    const mods = readModifications();
    if (!mods[relativePath]) mods[relativePath] = [];
    mods[relativePath].push(modification);
    writeModifications(mods);
    res.status(200).json({
      versionId: modification.id,
      diffSummary: modification.diffSummary,
      modifications: mods[relativePath],
    });
  } catch (e) {
    logError('modify', e);
    res.status(500).json({ error: e.message || 'Modification failed', detail: e.stack || e.message });
  }
});

function sanitizeBasename(name) {
  const base = path.basename(name || 'recording', path.extname(name || ''));
  return base.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80) || 'recording';
}

app.post('/api/export', express.json(), async (req, res) => {
  const relativePath = req.body?.path;
  const exportAudioOnly = !!req.body?.exportAudioOnly;
  const format = req.body?.format === 'wav' ? 'wav' : 'mp3'; // only used when exportAudioOnly
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'File not found' });
  }
  const filename = path.basename(absolutePath);
  const hash = filename.replace(/\.mp4$/i, '');
  const mixedPath = path.join(CACHE_ORIGINALS, `${hash}_mixed.wav`);
  const baseAudioPath = path.join(CACHE_ORIGINALS, `${hash}_audio.wav`);
  const audioPath = fs.existsSync(mixedPath) ? mixedPath : baseAudioPath;
  if (!fs.existsSync(audioPath)) {
    return res.status(400).json({ error: 'Audio not found for this file' });
  }
  const index = readOriginalsIndex();
  const entry = index[filename] || {};
  const originalName = entry.originalFilename || filename;
  const baseName = sanitizeBasename(originalName);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19).replace('T', '_');
  const ext = exportAudioOnly ? (format === 'wav' ? '.wav' : '.mp3') : '.mp4';
  const exportFilename = `vibe_edit_${baseName}_${timestamp}${ext}`;
  const exportPath = path.join(CACHE_EXPORTS, exportFilename);

  let err = null;
  if (exportAudioOnly) {
    err = await runExportAudio(audioPath, exportPath, format);
  } else {
    err = await runExportVideo(absolutePath, audioPath, exportPath);
  }
  if (err) {
    logError('export', new Error(err));
    return res.status(500).json({ error: err, detail: err });
  }
  res.status(200).json({
    downloadUrl: `/api/export/download?file=${encodeURIComponent(exportFilename)}`,
    filename: exportFilename,
    path: `cache/exports/${exportFilename}`,
  });
});

app.get('/api/export/download', (req, res) => {
  const file = req.query?.file;
  if (!file || typeof file !== 'string' || file.includes('..') || path.isAbsolute(file)) {
    return res.status(400).json({ error: 'Invalid file' });
  }
  const safe = path.basename(file);
  const absolute = path.join(CACHE_EXPORTS, safe);
  if (!fs.existsSync(absolute) || !absolute.startsWith(CACHE_EXPORTS)) {
    return res.status(404).json({ error: 'File not found' });
  }
  res.download(absolute, safe);
});

app.post('/api/undo', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  try {
    const mods = readModifications();
    const list = mods[relativePath] || [];
    if (list.length === 0) {
      return res.status(200).json({ modifications: [] });
    }
    list.pop();
    mods[relativePath] = list;
    writeModifications(mods);
    res.status(200).json({ modifications: list });
  } catch (e) {
    logError('undo', e);
    res.status(500).json({ error: e.message || 'Undo failed', detail: e.stack || e.message });
  }
});

app.post('/api/analyze', express.json(), (req, res) => {
  const relativePath = req.body?.path;
  if (!relativePath || typeof relativePath !== 'string') {
    return res.status(400).json({ error: 'Missing path' });
  }
  const absolutePath = path.resolve(__dirname, relativePath);
  const relToCache = path.relative(CACHE_ORIGINALS, absolutePath);
  if (relToCache.startsWith('..') || path.isAbsolute(relToCache)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(absolutePath)) {
    return res.status(404).json({ error: 'File not found' });
  }
  runAnalysis(absolutePath).then((result) => {
    if (result.error) {
      logError('analyze', new Error(result.error));
      return res.status(500).json({ error: result.error, detail: result.error });
    }
    const filename = path.basename(absolutePath);
    const index = readOriginalsIndex();
    if (index[filename]) {
      const snippet = typeof result.analysis === 'string'
        ? result.analysis.slice(0, 500)
        : '';
      index[filename].analysisSnippet = snippet;
      writeOriginalsIndex(index);
    }
    res.status(200).json({
      analysis: result.analysis,
      durationFormatted: result.durationFormatted ?? null,
    });
  });
});

app.post('/api/upload', upload.single('recording'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  const absolutePath = path.resolve(req.file.path);
  let relativePath = path.relative(__dirname, req.file.path).replace(/\\/g, '/');

  const validation = await runValidation(absolutePath);

  if (!validation.ok) {
    try { fs.unlinkSync(absolutePath); } catch { /* ignore */ }
  } else {
    try {
      const hash = await computeFileHash(absolutePath);
      const videoFilename = `${hash}.mp4`;
      const audioFilename = `${hash}_audio.wav`;
      const destVideo = path.join(CACHE_ORIGINALS, videoFilename);
      const destAudio = path.join(CACHE_ORIGINALS, audioFilename);

      fs.copyFileSync(absolutePath, destVideo);
      const extractErr = await runExtractAudio(destVideo, destAudio);
      if (extractErr) {
        fs.unlinkSync(destVideo);
        const msg = `Audio extraction failed: ${extractErr}`;
        logError('upload', new Error(msg));
        return res.status(500).json({ error: msg, detail: extractErr });
      }

      const index = readOriginalsIndex();
      index[videoFilename] = {
        hash,
        uploadDate: new Date().toISOString(),
        duration: validation.duration ?? null,
        durationFormatted: validation.durationFormatted ?? null,
        originalFilename: req.file.originalname ?? null,
        analysisSnippet: '',
      };
      writeOriginalsIndex(index);

      fs.unlinkSync(absolutePath);
      relativePath = path.join('cache', 'originals', videoFilename).replace(/\\/g, '/');
    } catch (err) {
      logError('upload', err);
      return res.status(500).json({ error: err.message || 'Cache failed', detail: err.stack || err.message });
    }
  }

  res.status(200).json({
    path: relativePath,
    originalName: req.file.originalname,
    filename: req.file.filename,
    validation: {
      ok: validation.ok,
      error: validation.error ?? null,
      durationFormatted: validation.durationFormatted ?? null,
    },
  });
});

app.use((err, _req, res, _next) => {
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ error: err.message });
  }
  res.status(400).json({ error: err.message || 'Upload failed' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Song Studio running at http://localhost:${PORT}`);
  console.log(`Cache: ${CACHE_ORIGINALS}`);
});
