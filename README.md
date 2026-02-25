# Song Element Analyzer (EDM-Rap / Trap Hybrid)

Free Streamlit web app to:

- Upload a song recording (`wav`, `mp3`, `m4a`, `flac`, `ogg`, `aac`)
- Detect BPM
- Timestamp common modern EDM-rap/trap layers (kick, 808, hats, vocals, risers, impacts, etc.)
- Recommend similar GarageBand sounds/patches per timestamp
- Suggest likely effects used to recreate each detected layer (including vocal FX chains)
- Export a **GarageBand-importable MIDI blueprint** for arrangement ripping/editing
- Generate a **copy/paste GarageBand build sheet** with track-by-track timestamp instructions
- Run a **post-rip MIDI analyzer** to score how close your MIDI is to the original structure
- Run an **AI stem-separated analysis mode (Demucs)** before timestamping layers

## What it does

The app analyzes the uploaded mix with spectral + rhythmic heuristics and generates:

- **BPM estimate**
- **Timestamped layer table**
- **Timeline chart of detected elements**
- **GarageBand patch/effects suggestions** for every detection
- **GarageBand MIDI blueprint** (editable regions/tracks after import)
- **Copy/paste build sheet** + TSV track sheet for fast recreation workflow
- **Post-rip MIDI quality report** (tempo/arrangement/timing/density/format checks)
- **AI stem-separated source routing** (drums/bass/vocals/other for cleaner detection)
- **CSV/JSON export** of analysis data

The detection model focuses on modern production building blocks used in styles like:

- Hybrid Trap
- Rage
- Phonk-EDM
- Jersey-club influenced rap beats
- General EDM-rap production

## Quick start

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the web app

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal (typically `http://localhost:8501`).

## Deploy free (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Click **New app** and select this repository/branch.
4. Set the main file path to `app.py`.
5. Deploy.

Streamlit Community Cloud will install `requirements.txt` automatically.

## Usage

1. Upload a song file.
2. Pick a subgenre profile (optional but recommended).
3. Select analysis mode:
   - `AI Stem-Separated (Demucs)` for highest-quality separation workflow
   - `Fast Mix Heuristic` for quicker fallback mode
4. Click **Analyze Song**.
4. Review:
   - BPM
   - Timestamped detections
   - GarageBand sound + patch + FX recommendations
   - GarageBand MIDI blueprint + copy/paste build sheet
   - Post-rip MIDI quality score and fix recommendations
5. Export results as CSV or JSON.

## GarageBand import workflow (rip + edit)

1. Run analysis and download **`garageband_blueprint.mid`**.
2. In GarageBand, create/open your project and set tempo to the detected BPM.
3. Drag `garageband_blueprint.mid` into GarageBand:
   - Each detected layer appears as an editable MIDI lane/region guide.
4. Download/open **`garageband_build_sheet.txt`** and follow:
   - Suggested patch/similar sound per layer
   - FX chain suggestions
   - Timestamp region cues
5. Replace blueprint MIDI sounds with your preferred GarageBand instruments and edit.
6. Run the in-app **Post-Rip MIDI Analyzer** to verify closeness against the original upload.
7. Optionally export your edited GarageBand MIDI and upload it back for re-check.

## Notes on accuracy

- In `AI Stem-Separated (Demucs)` mode, separation quality is model-driven and substantially closer to true stems.
- In `Fast Mix Heuristic` mode, detections are estimated directly from the mixed audio.
- Results are meant as a **production recreation assistant**, not a legal/forensic transcription.
- Use your ears to refine patch/effect choices after loading the recommended GarageBand starting points.
- MIDI quality checks validate structure/timing similarity; they cannot guarantee identical mastering or sound design.

## About "exact" stem separation

This app now includes **AI stem-separated mode via Demucs** (substantially closer to true stems than mix-only heuristics).
However, exact mathematically perfect separation from a single mastered stereo file is generally not physically guaranteed.
Use Demucs mode + the post-rip MIDI analyzer loop to get the closest practical reconstruction.

## Project structure

```text
app.py                         # Streamlit UI
song_analyzer/analysis.py      # Audio feature extraction + element detection
song_analyzer/pipeline.py      # Mix vs AI stem-separated orchestration
song_analyzer/garageband.py    # GarageBand patch/effects mapping
song_analyzer/garageband_export.py  # GarageBand MIDI + copy/paste export helpers
song_analyzer/midi_quality.py  # Post-rip MIDI comparison and quality scoring
song_analyzer/stem_separation.py # Demucs stem extraction helpers
requirements.txt
```