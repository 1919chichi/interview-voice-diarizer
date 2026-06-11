# Design: Local Interview Voice Diarizer CLI

## Architecture

The CLI exposes `ivd debrief <audio-path>`. It prepares the audio, submits it to Volcengine ASR, normalizes utterances into `Speaker N` transcript turns, asks a chat model to infer roles and evaluate answers, then writes Markdown and JSON artifacts.

## Components

- `audio.py`: validates input files, probes codecs with `ffprobe`, and converts unsupported formats to `.mp3` with `ffmpeg`.
- `volcengine.py`: calls Volcengine speech recognition and Volcengine Ark-compatible chat completions.
- `models.py`: defines normalized transcript and debrief data models.
- `analysis.py`: builds prompts, parses model JSON, and contains a deterministic fallback role heuristic.
- `report.py`: renders transcript and review Markdown.
- `cli.py`: parses command-line options and coordinates the workflow.

## Data Flow

1. User runs `ivd debrief recording.m4a`.
2. CLI creates `outputs/recording/`.
3. Audio is copied or converted to a supported upload file.
4. ASR returns raw JSON and utterance-level speaker segments.
5. Transcript turns are normalized and saved.
6. Chat analysis returns role mapping, question list, answer defects, suggestions, and learning points.
7. CLI writes `raw-asr.json`, `summary.json`, `transcript.md`, and `qa-review.md`.

## Error Handling

- Missing audio path fails before API calls.
- Missing `ffmpeg` or `ffprobe` fails with an installation hint.
- Unsupported or unreadable `.qma` fails with an explicit export hint.
- Missing API keys fails with the exact environment variable name.
- Invalid LLM JSON falls back to heuristic role mapping and a minimal summary, while preserving raw ASR output.
