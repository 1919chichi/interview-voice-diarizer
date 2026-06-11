# Proposal: Build Local Interview Voice Diarizer CLI

## Intent

Create a local command-line tool that turns interview recordings into actionable interview debrief reports.

## Scope

- Accept a local recording path from the CLI.
- Support `.m4a` and `.qma` through `ffmpeg` probing and conversion, plus direct `.wav`, `.mp3`, and `.ogg` input.
- Call Volcengine speech recognition with speaker separation enabled.
- Infer which speaker is the interviewer and which speaker is the candidate.
- Generate local transcript and review artifacts.

## Out of Scope

- Web upload UI.
- Database-backed interview history.
- Feishu document export.
- Bypassing encrypted or protected `.qma` files.

## Approach

Use a Python CLI with small focused modules: audio preparation, Volcengine ASR client, role and interview analysis, Markdown rendering, and CLI orchestration. Store all outputs under a per-recording output directory.
