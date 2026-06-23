# interview-voice-diarizer

[中文](README.md)

A local CLI for post-interview audio debriefs. It sends recordings to Volcengine ASR, normalizes transcripts and speaker information, identifies interviewer and candidate roles, and generates a full transcript, a question-by-question review, and a structured summary.

## Features

- Uploads local `.wav`, `.mp3`, and `.ogg` files directly.
- Transcodes `.m4a`, `.qma`, `.mp4`, `.aac`, and `.flac` files to 16 kHz MP3 with `ffmpeg` before upload.
- Supports local-file recognition with Volcengine ASR Flash and public audio URL submission and polling with Standard ASR.
- Requests utterance and speaker information, then checks that multiple speakers were not accidentally collapsed during normalization.
- Infers interviewer, candidate, or unknown roles from each speaker's question and answer evidence, including cases where multiple speaker clusters belong to one role.
- Uses Volcengine Ark for in-depth analysis by default, or runs a fully local heuristic review with `--skip-analysis`.
- Rebuilds reports from a historical `raw-asr.json` without uploading the audio or calling ASR again.
- Writes Markdown transcripts, Markdown Q&A reviews, and JSON summaries.

## Pipeline

```text
Local recording / public audio URL
        |
        v
Audio probing and optional transcoding
        |
        v
Volcengine ASR -> raw-asr.json
        |
        v
Transcript normalization -> speaker validation -> role inference -> debrief analysis
        |
        v
transcript.md + qa-review.md + summary.json
```

The CLI saves `raw-asr.json` before Ark analysis. If analysis fails, use `ivd reanalyze` to continue from that file without transcribing a long recording again.

## Requirements

- Python 3.11+
- [`ffmpeg` and `ffprobe`](https://ffmpeg.org/documentation.html)
- [Volcengine ASR API Key](https://www.volcengine.com/docs/6561/80816)
- For full model analysis, a [Volcengine Ark API Key and model Endpoint ID](https://www.volcengine.com/docs/82379/1099455)

## Installation

```bash
git clone <repo-url>
cd interview-voice-diarizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Verify the installed CLI:

```bash
ivd --help
```

## Configuration

```bash
cp .env.example .env
```

Minimum configuration:

```dotenv
VOLC_ASR_API_KEY=your-volcengine-asr-api-key
VOLC_ARK_API_KEY=your-volcengine-ark-api-key
VOLC_ARK_MODEL=your-ark-model-endpoint-id
```

`VOLC_ARK_API_KEY` and `VOLC_ARK_MODEL` are not required when using `--skip-analysis`. The code also supports these optional variables:

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `VOLC_ASR_RESOURCE_ID` | `volc.seedasr.auc` | Standard ASR resource ID |
| `VOLC_ASR_FLASH_RESOURCE_ID` | `volc.bigasr.auc_turbo` | Flash ASR resource ID |
| `VOLC_ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | Ark OpenAI-compatible API base URL |
| `VOLC_ARK_TIMEOUT_SECONDS` | `600` | Ark analysis request timeout in seconds; increase it for long recordings |
| `VOLC_ARK_MAX_TOKENS` | `16000` | Ark review JSON output token limit; helps avoid truncated long reports |

You can pass all settings through process environment variables instead. To use a code default, omit the optional variable rather than setting it to an empty string.

## Usage

### Analyze a local recording

The default `flash` mode reads a local file:

```bash
ivd debrief "/path/to/recording.m4a" \
  --company "Acme Corp" \
  --role "Backend Engineer" \
  --round "Round 1"
```

Common options:

```bash
# Choose an output directory
ivd debrief "/path/to/recording.mp3" --output-dir "/path/to/output"

# Skip Ark and generate a heuristic review only
ivd debrief "/path/to/recording.mp3" --skip-analysis
```

### Analyze a public audio URL

`standard` mode submits `--audio-url` to Standard ASR. The positional argument is still used to derive the default output directory name, so specifying `--output-dir` is recommended:

```bash
ivd debrief "remote-interview.mp3" \
  --mode standard \
  --audio-url "https://example.com/interview.mp3" \
  --output-dir "outputs/remote-interview"
```

### Reanalyze historical ASR output

If `raw-asr.json` is available, you can apply the current transcript normalization, speaker role inference, and debrief logic:

```bash
ivd reanalyze "outputs/<recording-filename>/raw-asr.json" \
  --company "Acme Corp" \
  --role "Backend Engineer" \
  --round "Round 1"
```

This command never calls ASR. It uses Ark to rebuild a full review by default; for a fully local run, use:

```bash
ivd reanalyze "outputs/<recording-filename>/raw-asr.json" --skip-analysis
```

Reports are written to the directory containing `raw-asr.json` by default. Use `--output-dir` to choose another location. Before existing reports are replaced, they are copied to:

```text
outputs/<recording-filename>/backups/reanalysis-YYYYMMDD-HHMMSS/
├── summary.json
├── transcript.md
└── qa-review.md
```

The original `raw-asr.json`, recording, and transcoded audio are never modified. Invalid JSON, speaker validation failures, or Ark errors also leave existing reports unchanged.

## Output

The default output directory is `outputs/<recording-filename>/`:

```text
outputs/<recording-filename>/
├── converted.mp3      # Only created when a local input needs transcoding
├── raw-asr.json       # Raw Volcengine ASR response
├── summary.json       # Role mapping and structured debrief
├── transcript.md      # Full conversation with timestamps and role labels
└── qa-review.md       # Questions, answers, gaps, suggestions, and learning points
```

## Audio Formats and Limitations

- `.wav`, `.mp3`, and `.ogg` are uploaded directly after being probed with `ffprobe`.
- `.m4a`, `.qma`, `.mp4`, `.aac`, and `.flac` preserve up to two channels and are transcoded to 16 kHz, 64 kbps MP3.
- `.qma` is not an explicitly supported Volcengine ASR format and only works when `ffprobe` and `ffmpeg` can decode it.
- This project does not decrypt or bypass protected audio. Export undecodable recordings as `.m4a`, `.mp3`, or `.wav` from the source application.
- The ASR request language is currently fixed to `zh-CN`.

## Development and Verification

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
```

The project uses a flat `src/` layout and exposes `cli:app` as its CLI entry point. Its core modules are:

```text
src/
├── cli.py
├── config.py
├── errors.py
├── models.py
├── providers/volcengine.py
├── pipeline/{audio,transcript,analysis,debrief}.py
└── output/report.py
```

## Privacy

`.gitignore` excludes `.env`, common recording formats, `outputs/`, and generated reports. Never commit API keys, interview recordings, `raw-asr.json`, or output containing candidate data.

## Related Documentation

- [Volcano Engine ASR API](https://www.volcengine.com/docs/6561/80816)
- [Volcano Ark LLM API](https://www.volcengine.com/docs/82379/1099455)
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
