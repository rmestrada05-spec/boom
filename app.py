"""Streamlit web app for EDM-rap song element timestamping and recreation help."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from song_analyzer.analysis import analyze_song
from song_analyzer.garageband_export import (
    build_garageband_blueprint_midi,
    build_garageband_blueprint_text,
    build_garageband_blueprint_tsv,
)


SUPPORTED_TYPES = ["wav", "mp3", "m4a", "flac", "ogg", "aac"]
SUBGENRE_OPTIONS = [
    "General EDM-rap",
    "Hybrid Trap",
    "Rage",
    "Phonk-EDM",
    "Jersey-club Influenced",
]


def _detections_to_dataframe(detections: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for detection in detections:
        rows.append(
            {
                "Element": detection["element"],
                "Start": detection["start_timestamp"],
                "End": detection["end_timestamp"],
                "Start (s)": detection["start_seconds"],
                "End (s)": detection["end_seconds"],
                "Confidence": detection["confidence"],
                "GarageBand Similar Sound": detection["garageband_similar_sound"],
                "GarageBand Patch": detection["garageband_patch"],
                "Suggested Effects": " | ".join(detection["suggested_effects"]),
                "Recreation Notes": detection["recreation_notes"],
            }
        )
    return pd.DataFrame(rows)


def _timeline_chart(df: pd.DataFrame) -> alt.Chart:
    chart_df = df[["Element", "Start (s)", "End (s)", "Confidence"]].copy()
    chart_df = chart_df.sort_values(["Start (s)", "Element"])
    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y("Element:N", sort="-x", title="Detected Layer"),
            x=alt.X("Start (s):Q", title="Song Time (seconds)"),
            x2=alt.X2("End (s):Q"),
            color=alt.Color("Confidence:Q", scale=alt.Scale(scheme="turbo")),
            tooltip=["Element", "Start (s)", "End (s)", "Confidence"],
        )
        .properties(height=500)
    )


def main() -> None:
    st.set_page_config(page_title="Song Element Analyzer", layout="wide")

    st.title("Song Element Analyzer + GarageBand Recreation Assistant")
    st.write(
        "Upload a track and get timestamped layer detection, BPM, and GarageBand sound/effect "
        "suggestions so you can rebuild the production."
    )

    with st.expander("What this app detects", expanded=False):
        st.markdown(
            "- Core rhythm & low-end (kick, 808/sub, snare/clap, hats, percussion)\n"
            "- Melodic/harmonic layers (lead, pads/chords, counter melodies, stabs)\n"
            "- Vocal layers (main vocal, ad-libs, chops, vocal FX, one-shots)\n"
            "- EDM FX and transitions (risers, impacts, sweeps, textures, fills)\n"
            "- Optional modern layers (growls, counter 808s, reese, plucks, supersaw)"
        )

    col_left, col_right = st.columns([2, 1])
    with col_left:
        uploaded_file = st.file_uploader("Upload a song recording", type=SUPPORTED_TYPES)
    with col_right:
        selected_subgenre = st.selectbox("Subgenre profile", options=SUBGENRE_OPTIONS, index=0)

    analyze_clicked = st.button("Analyze Song", type="primary", disabled=uploaded_file is None)

    if not analyze_clicked:
        return
    if uploaded_file is None:
        st.warning("Upload an audio file to begin.")
        return

    suffix = Path(uploaded_file.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_path = temp_file.name

    try:
        with st.spinner("Analyzing song layers, BPM, and GarageBand matches..."):
            result = analyze_song(temp_path, subgenre_profile=selected_subgenre)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Analysis failed: {exc}")
        return
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass

    bpm_col, duration_col, conf_col = st.columns(3)
    bpm_col.metric("Detected BPM", f"{result['bpm']}")
    duration_col.metric("Track Duration (s)", f"{result['duration_seconds']}")
    conf_col.metric("Avg Detection Confidence", f"{result['overall_detection_confidence']}")

    detections = result["detections"]
    if not detections:
        st.warning(
            "No strong layer detections were found. Try a cleaner master file or a different subgenre profile."
        )
        return

    detections_df = _detections_to_dataframe(detections)
    st.subheader("Timestamped Layer Breakdown")
    st.dataframe(detections_df, use_container_width=True, height=420)

    st.subheader("Timeline View")
    st.altair_chart(_timeline_chart(detections_df), use_container_width=True)

    st.subheader("Layer Count Summary")
    summary_df = (
        detections_df.groupby("Element", as_index=False)["Confidence"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"count": "Detections", "mean": "Avg Confidence"})
        .sort_values(["Detections", "Avg Confidence"], ascending=[False, False])
    )
    summary_df["Avg Confidence"] = summary_df["Avg Confidence"].round(3)
    st.dataframe(summary_df, use_container_width=True)

    st.subheader("GarageBand Rip-Off Kit (Import + Copy/Paste)")
    st.markdown(
        "This section gives you assets you can directly use in GarageBand:\n"
        "1. **MIDI Blueprint**: import into GarageBand to create editable arrangement lanes.\n"
        "2. **Build Sheet (TXT)**: copy/paste track setup + FX chain + timestamps.\n"
        "3. **Track Sheet (TSV)**: paste into Notes/Sheets for detailed editing."
    )
    midi_data = build_garageband_blueprint_midi(detections, bpm=result["bpm"])
    blueprint_text = build_garageband_blueprint_text(result)
    blueprint_tsv = build_garageband_blueprint_tsv(detections)

    import_col_1, import_col_2, import_col_3 = st.columns(3)
    with import_col_1:
        st.download_button(
            "Download MIDI Blueprint (.mid)",
            data=midi_data,
            file_name="garageband_blueprint.mid",
            mime="audio/midi",
        )
    with import_col_2:
        st.download_button(
            "Download Build Sheet (.txt)",
            data=blueprint_text.encode("utf-8"),
            file_name="garageband_build_sheet.txt",
            mime="text/plain",
        )
    with import_col_3:
        st.download_button(
            "Download Track Sheet (.tsv)",
            data=blueprint_tsv.encode("utf-8"),
            file_name="garageband_track_sheet.tsv",
            mime="text/tab-separated-values",
        )

    st.caption(
        "Copy this text directly (Cmd+A/Cmd+C) into your notes while producing, then mirror "
        "its track list/effect chain in GarageBand."
    )
    st.text_area(
        "Copy/Paste GarageBand Build Sheet",
        value=blueprint_text,
        height=420,
    )

    st.subheader("Export Results")
    csv_data = detections_df.to_csv(index=False).encode("utf-8")
    json_data = json.dumps(result, indent=2).encode("utf-8")
    export_col_1, export_col_2 = st.columns(2)
    with export_col_1:
        st.download_button(
            "Download CSV (timestamps + GarageBand mapping)",
            data=csv_data,
            file_name="song_element_timestamps.csv",
            mime="text/csv",
        )
    with export_col_2:
        st.download_button(
            "Download JSON (full analysis)",
            data=json_data,
            file_name="song_analysis.json",
            mime="application/json",
        )

    st.subheader("Important Notes")
    for note in result["notes"]:
        st.write(f"- {note}")


if __name__ == "__main__":
    main()
