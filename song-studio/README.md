# Song Studio

Upload and validate screen recordings for song analysis. **Single-window, tabbed app** — all features (Studio, Voice, Customize) are available at once without restarting or leaving the app.

## Run the app

```bash
cd song-studio
npm install
npm start
```

**Step 2 validation** requires Python 3 and MoviePy:

```bash
pip install -r requirements.txt
# or: pip install moviepy
```

Open **http://localhost:3000**. The Studio tab has an orange (#FF8000) background with a prominent **Upload Screen Recording** button.

## Features

### Step 1 – Upload
- **Upload Screen Recording** button: orange background, black text, large font.
- **Formats**: .mp4, .mov, .mkv, .avi.
- After selecting a file: **Validating & Loading…** spinner.
- When done: file name and duration (e.g. `song_clip.mp4 – 3:42`).
- Working copy stored in `./cache/originals/{timestamp_filename}`.

### Step 2 – Validate (not corrupted, can play fully)
- **Check 1**: File exists and size > 1 KB.
- **Check 2**: Opens with `moviepy.VideoFileClip` without exception.
- **Check 3**: Duration readable and > 5 seconds.
- **Check 4**: Audio duration ≈ video duration (±0.5 s).
- **Check 5**: Seek to 10%, 50%, 90% and read frame + audio sample without error.
- **If any check fails**: Red error banner at top: “File appears corrupted or unreadable. Please try another recording.” with **Retry** button.
- **If all pass**: Green toast: “File validated successfully (Duration: X:XX)”.

### Step 3 – Analyze song parts (no stems)
- **Librosa only** on the full mixed audio (no Demucs).
- **Four numbered sections** in a scrollable, monospaced text area:
  1. **Functional Musical Layers** – each role with detected presence/confidence (e.g. Percussion, Bass, Melody/Keys, Pad).
  2. **Vocal Specifics** – e.g. “High confidence vocal presence”, “Possible vocal presence”.
  3. **Structural Parts** – approximate time ranges in mm:ss (Intro, Verse, Chorus, Bridge, Outro) with confidence (e.g. “High confidence chorus repetition”).
  4. **Descriptive Terms for Sound** – e.g. tempo, bright/dark, dynamics, harmonic/percussive.
- **Heuristics**: onset detection, beat tracking, spectral centroid/rolloff, RMS, chroma-based novelty for structure boundaries.
- **Target**: analysis runs in < 30 seconds on average song length.
- After validation, click **Analyze song parts**; results appear in the text area below.

### Step 4 – Cache the original song permanently
- After successful validation:
  - Video is copied to `./cache/originals/{sha256_hash}.mp4`.
  - Audio is extracted to `./cache/originals/{sha256_hash}_audio.wav` (48 kHz, 16-bit PCM).
- Index file `./cache/originals_index.json` maps each cached filename to: `hash`, `uploadDate`, `duration`, `durationFormatted`, `originalFilename`, `analysisSnippet` (filled when you run analysis).

### Step 5 – Vague chat-based modification of song parts
- **Chat input** below the analysis area: “Describe your change” with example placeholder (e.g. make bass in intro deeper but keep vibe, raise vocal pitch in chorus by ~3 semitones, add subtle reverb to pads).
- **Natural-language parsing** (heuristic) for: target stem/layer (bass, drums, vocals, harmonic, pads, keys), section (intro, verse, chorus, bridge, outro), modification type (pitch, tempo, volume, reverb, eq, distortion), direction/amount (e.g. +3 semitones, subtle, deeper), and preserve intent (“keep vibe/essence/groove”).
- **After applying**: a new version is stored, a **diff summary** is shown (e.g. “Bass pitch shifted +2 semitones in 0:00–0:45”) in a version history list.
- **Undo** reverts to the previous version (removes last modification from history).
- Version history is stored in `./cache/modifications.json` (keyed by file path).

### Step 6 – Save finished product to device
- **Bottom of Studio tab**: checkbox **Export audio only** and a large **Save Finished Product** button.
- **If “Export audio only” is checked**: choose **MP3 (320 kbps)** or **WAV**; export is saved with that format.
- **If unchecked**: original video is re-exported with the cached audio (moviepy: H.264 + AAC) as **.mp4**.
- **Default filename**: `vibe_edit_{original_name}_{timestamp}.mp4` (or `.mp3` / `.wav` for audio-only).
- After save: the **path** is shown and an **Open in Finder** button opens the download in a new tab (re-download so you can open your Downloads folder).
- Exports are written to `./cache/exports/` and served for download.

### Step 7 – FL Studio aesthetic (simplified)
- **Dark theme**: base background `#1E1E1E`, accent buttons `#FF8000` (FL-style orange).
- **Channel-rack layout**: vertical panels for **Upload**, **Analysis**, **Chat**, **Versions**, **Save** (no complex mixer, piano roll, or playlist).
- **3 tabs only**: **Studio** (main), **Voice**, **Customize**.
- **Large readable fonts**, generous padding, minimal nested menus.

### Step 11 – All features in one cohesive app
- **Single window**: one browser tab, one layout; no separate “modes” or extra windows for core features.
- **Tabbed interface**: **Studio** (upload, analysis, chat, versions, save), **Voice** (phrase sets for voice forging), **Customize** (theme swatches). Switch tabs anytime — no restart and no context switch; session state (loaded file, theme, modifications) is kept.

### Step 8 – Color customization tab
- **Customize** tab: grid of **8 preset color swatches** (FL Studio, Ocean, Forest, Sunset, Mono, Cherry, Midnight, Lavender).
- Each swatch shows the **accent color** and **name**; clicking one **instantly** updates window background, button accents, and text areas.
- Choice is saved to **`./cache/user_settings.json`** (`theme` key) and **persists across runs**; loaded on app start.

### Step 14 – Add external audio/video layers
- **Layers** panel in Studio: button **Add Audio/Video Layer** → file picker (audio or video). If video, the audio track is extracted.
- **Mix mode** (user choice): **Overlay at 50% volume**, **Replace section** (with start/end time in seconds), **Append**, **Sidechain ducking**.
- A new version is created after adding (listed in Versions). Mixed result is stored as `cache/originals/{hash}_mixed.wav` and used for export when present.
- Depends on `scripts/mix_audio.py` (pydub) and `pip install pydub` (ffmpeg required for pydub).

### Step 12 – Dedicated Voice tab (upload, modify, versions, save)
- **Voice** tab has its own: **Upload** (Upload Voice Recording), **Analysis** (loaded file info), **Chat** (describe changes — pitch, formant, reverb, etc.), **Versions** dropdown (Original, v1 – …, v2 – …), **Save** (Save Voice → WAV in exports).
- Modifications apply **only to the voice track** (parsed intent stored per voice file; actual audio processing can be wired later).
- Voice files are stored in `./cache/voices/originals/{hash}.wav` (uploaded audio/video converted to 48 kHz WAV). Version history in `./cache/voice_modifications.json`.

### Step 13 – Language-specific phonetic phrase sets (Voice tab)
- **Voice** tab: text input **“Enter language (e.g., English, Spanish, Japanese, Russian, or any other)”**, optional **“Enter tone/style”** (e.g. normal, screamo, whisper).
- **Get Phrases** button: calls `GET /api/voice/phrases?lang=...` and shows **4–8 phonetically balanced sentences** for that language (predefined sets for English, Spanish, Japanese, Russian). For unsupported languages, shows fallback: *“Unsupported language – use English phrases as a base and speak in your target language.”* with suggested English phrases.
- Instructions: *“Record yourself clearly saying each phrase 2–3 times for best voice cloning results.”*
- FL Studio dark theme and orange accent for the tab.

### Step 9 – File corruption checking
- **Step 2 validation** (MoviePy: file exists, size > 1 KB, opens as video, duration > 5 s, audio ≈ video, seek 10%/50%/90%) is applied to **every file upload** (video now; same logic for future audio, voice, layers).
- On failure: **consistent red banner** at top with **detailed error reason** (e.g. “No audio track in file”, “Duration must be > 5 seconds (got 2.1s)”) and **Retry** button.
- Upload/network errors use the same banner with the returned error message.

## Project layout

- `public/index.html` – Studio tab, error banner, toast
- `public/styles.css` – Studio theme, banner, toast
- `public/app.js` – upload, validation UI, retry
- `server.js` – uploads to `cache/originals/`, runs Python validator
- `scripts/validate_recording.py` – MoviePy validation (5 checks)
- `scripts/analyze_song_parts.py` – Librosa analysis (4 sections, < 30 s)
- `scripts/extract_audio.py` – Extract 48 kHz 16-bit WAV from video (Step 4)
- `scripts/export_audio.py` – Export WAV/MP3 (Step 6)
- `scripts/export_video.py` – Re-attach audio to video, MP4 H.264+AAC (Step 6)
- `cache/originals/` – Permanent cache: `{hash}.mp4`, `{hash}_audio.wav`
- `cache/exports/` – Exported files: `vibe_edit_*`
- `cache/originals_index.json` – Index: filename → hash, upload date, duration, analysis snippet
- `cache/modifications.json` – Step 5: path → list of modification intents (version history)
- `cache/user_settings.json` – Step 8: user theme choice (persists across runs)
- `cache/voices/originals/` – Step 12: voice recordings as `{hash}.wav`
- `cache/voice_modifications.json` – Step 12: voice version history per file
- `scripts/convert_to_wav.py` – Step 12: any audio/video → 48 kHz WAV
- `scripts/mix_audio.py` – Step 14: mix layer into main (overlay50, replace, append, sidechain; pydub)
- `cache/layers_temp/` – Step 14: temp layer files before mix
- `requirements.txt` – Python deps (moviepy, librosa, numpy, pydub)
