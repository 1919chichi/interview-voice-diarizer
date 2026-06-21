## ADDED Requirements

### Requirement: Reanalyze a saved ASR response
The system SHALL provide an `ivd reanalyze <raw-asr.json>` command that regenerates derived reports from a saved ASR response without invoking ASR.

#### Scenario: Reanalyze valid historical data
- **WHEN** the user supplies a valid ASR JSON file containing usable utterances
- **THEN** the system normalizes speakers, analyzes roles, and writes `summary.json`, `transcript.md`, and `qa-review.md`

#### Scenario: Reanalyze without model analysis
- **WHEN** the user supplies `--skip-analysis`
- **THEN** the system performs deterministic local analysis without loading Ark or ASR configuration

### Requirement: Preserve the raw historical source
The system MUST NOT modify, move, or overwrite the supplied ASR JSON file during reanalysis.

#### Scenario: Reports are regenerated in the source directory
- **WHEN** the output directory defaults to the ASR JSON parent directory
- **THEN** the source JSON contents remain byte-for-byte unchanged

### Requirement: Back up existing derived reports
The system SHALL back up existing `summary.json`, `transcript.md`, and `qa-review.md` files after analysis succeeds and before new reports are written.

#### Scenario: Existing reports are present
- **WHEN** at least one derived report already exists
- **THEN** the system copies existing reports into a unique timestamped backup directory before replacing them

#### Scenario: Analysis fails
- **WHEN** JSON loading, transcript normalization, or model analysis fails
- **THEN** the system leaves existing reports unchanged and creates no backup

#### Scenario: No reports exist
- **WHEN** no derived report exists in the target directory
- **THEN** the system writes new reports without creating an empty backup directory

### Requirement: Validate historical input
The system SHALL report actionable errors for missing, non-file, malformed, or non-object JSON input.

#### Scenario: Historical JSON is malformed
- **WHEN** the supplied file cannot be decoded as a JSON object
- **THEN** the CLI exits non-zero without changing existing reports

### Requirement: Preserve shared report behavior
The `debrief` and `reanalyze` commands SHALL use the same ASR post-processing and report-writing implementation.

#### Scenario: Equivalent raw ASR input
- **WHEN** both commands process the same raw ASR response and metadata with the same analysis mode
- **THEN** they produce equivalent diagnostics, role mappings, transcripts, and review reports
