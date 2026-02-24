# Song Element Analyzer (EDM-Rap / Trap Hybrid)

Free Streamlit web app to:

- Upload a song recording (`wav`, `mp3`, `m4a`, `flac`, `ogg`, `aac`)
- Detect BPM
- Timestamp common modern EDM-rap/trap layers (kick, 808, hats, vocals, risers, impacts, etc.)
- Recommend similar GarageBand sounds/patches per timestamp
- Suggest likely effects used to recreate each detected layer (including vocal FX chains)

## What it does

The app analyzes the uploaded mix with spectral + rhythmic heuristics and generates:

- **BPM estimate**
- **Timestamped layer table**
- **Timeline chart of detected elements**
- **GarageBand patch/effects suggestions** for every detection
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

## Usage

1. Upload a song file.
2. Pick a subgenre profile (optional but recommended).
3. Click **Analyze Song**.
4. Review:
   - BPM
   - Timestamped detections
   - GarageBand sound + patch + FX recommendations
5. Export results as CSV or JSON.

## Notes on accuracy

- This is a **heuristic analysis engine** (not full stem separation).
- Results are meant as a **production recreation assistant**, not a legal/forensic transcription.
- Use your ears to refine patch/effect choices after loading the recommended GarageBand starting points.

## Project structure

```text
app.py                         # Streamlit UI
song_analyzer/analysis.py      # Audio feature extraction + element detection
song_analyzer/garageband.py    # GarageBand patch/effects mapping
requirements.txt
```