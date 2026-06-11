# Delta for Debrief CLI

## ADDED Requirements

### Requirement: Local Audio Input
The system SHALL accept a local audio file path through a CLI command.

#### Scenario: Existing recording path
- GIVEN a supported or convertible audio file exists on disk
- WHEN the user runs `ivd debrief <path>`
- THEN the system prepares the file for speech recognition

### Requirement: Audio Conversion
The system SHALL convert `.m4a` and decodable `.qma` files to an upload format supported by Volcengine ASR.

#### Scenario: M4A input
- GIVEN a `.m4a` recording exists
- WHEN the user runs the debrief command
- THEN the system converts it to `.mp3` before upload

#### Scenario: Undecodable QMA input
- GIVEN a `.qma` file cannot be decoded by `ffmpeg`
- WHEN the user runs the debrief command
- THEN the system fails with a message asking the user to export a standard audio format

### Requirement: Speaker Diarization
The system SHALL request utterance-level speaker information from Volcengine ASR.

#### Scenario: ASR response includes utterances
- GIVEN the ASR response contains utterances with speaker IDs
- WHEN the system normalizes the response
- THEN the transcript uses labels like `Speaker 0` and `Speaker 1`

### Requirement: Interview Debrief Output
The system SHALL generate local transcript and interview review files.

#### Scenario: Successful debrief
- GIVEN ASR and analysis complete
- WHEN the command finishes
- THEN `raw-asr.json`, `summary.json`, `transcript.md`, and `qa-review.md` exist in the output directory
