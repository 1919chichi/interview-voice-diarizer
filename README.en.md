# interview-voice-diarizer

A local CLI for post-interview audio debrief. Feed it a recording, and it automatically transcodes the audio to a format supported by Volcengine ASR, calls the API for transcription and speaker diarization, then generates interview questions, candidate answers, answer gaps, improvement suggestions, and follow-up learning points.

## Features

- Accepts local `.m4a`, `.qma`, `.wav`, `.mp3`, `.ogg` input.
- Unsupported formats are automatically transcoded to `.mp3` via `ffmpeg` before upload.
- Calls Volcengine ASR API with speaker diarization and utterance output enabled.
- Automatically infers which speaker is the interviewer and which is the candidate.
- Outputs local Markdown and JSON files.

## Requirements

- Python 3.11+
- `ffmpeg` and `ffprobe`
- Volcengine ASR API Key
- Volcengine Ark API Key and model Endpoint ID

## Installation

```bash
git clone <repo-url>
cd interview-voice-diarizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Configuration

```bash
cp .env.example .env
```

Fill in:

```bash
VOLC_ASR_API_KEY=your-volcengine-asr-api-key
VOLC_ARK_API_KEY=your-volcengine-ark-api-key
VOLC_ARK_MODEL=your-ark-model-endpoint-id
```

You can also pass these as environment variables directly.

## Usage

```bash
ivd debrief "/path/to/recording.m4a" \
  --company "Acme Corp" \
  --role "Backend Engineer" \
  --round "Round 1"
```

Output directory (default: `outputs/<recording-filename>/`):

```text
outputs/<recording-filename>/
├── converted.mp3
├── raw-asr.json
├── summary.json
├── transcript.md
└── qa-review.md
```

## Note on `.qma` files

`.qma` is not an officially documented format for Volcengine ASR. The CLI will attempt to decode it using `ffprobe`/`ffmpeg`:

- If decodable, it will be transcoded to `.mp3` before upload.
- If not decodable, an error is raised with a prompt to export the recording as `.m4a`, `.mp3`, or `.wav` from the source app.

Encrypted or DRM-protected audio is not supported.
