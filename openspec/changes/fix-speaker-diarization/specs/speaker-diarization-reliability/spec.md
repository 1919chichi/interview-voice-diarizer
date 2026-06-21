## ADDED Requirements

### Requirement: Normalize speaker identifiers without loss
The system SHALL read speaker identifiers from supported utterance fields, including nested `additions.speaker`, and SHALL preserve numeric zero as a valid identifier.

#### Scenario: Volcengine returns nested speaker identifiers
- **WHEN** an ASR utterance contains `additions.speaker`
- **THEN** the normalized turn uses that value as its `Speaker N` label

#### Scenario: An utterance has no speaker identifier
- **WHEN** an ASR utterance contains text but no supported speaker field
- **THEN** the normalized turn is labeled `Speaker unknown` rather than a fabricated numeric speaker

### Requirement: Detect speaker normalization loss
The system SHALL compare raw and normalized speaker cardinality without logging transcript content.

#### Scenario: Multiple raw speakers collapse during normalization
- **WHEN** the raw ASR response contains at least two distinct speaker identifiers and normalized turns contain fewer than two
- **THEN** the CLI stops analysis with an actionable error after preserving `raw-asr.json`

### Requirement: Aggregate speaker clusters into interview roles
The system SHALL support mapping multiple Speaker identifiers to the interviewer or candidate role while preserving a primary Speaker anchor for compatibility.

#### Scenario: ASR over-segments two people
- **WHEN** the transcript contains more than two Speaker identifiers
- **THEN** every known Speaker receives an interviewer, candidate, or unknown role assignment and multiple Speakers may share one role

#### Scenario: Transcript contains exactly two speakers
- **WHEN** question and answer evidence identifies two different Speakers
- **THEN** the system maps one to interviewer and the other to candidate

### Requirement: Degrade safely when roles are indeterminate
The system MUST NOT assign the same Speaker as both interviewer and candidate.

#### Scenario: Transcript contains one speaker
- **WHEN** all normalized turns have the same Speaker identifier
- **THEN** interviewer and candidate anchors are unset, confidence is low, and transcript labels remain unchanged

### Requirement: Validate model-provided role mappings
The system SHALL accept model role assignments only for Speaker identifiers present in the transcript and SHALL restrict assignments to known role labels.

#### Scenario: Model references a nonexistent speaker
- **WHEN** the model returns a role mapping containing a Speaker not present in the transcript
- **THEN** the system rejects that mapping and uses the deterministic fallback mapping

#### Scenario: Model omits a known speaker
- **WHEN** an otherwise valid model mapping omits a Speaker present in the transcript
- **THEN** the system fills the missing assignment from the deterministic fallback

### Requirement: Preserve useful source channel information
The system SHALL avoid unconditional stereo-to-mono downmixing during required format conversion.

#### Scenario: Convertible input has one audio channel
- **WHEN** ffprobe reports a mono source
- **THEN** the converted upload remains mono

#### Scenario: Convertible input has two or more audio channels
- **WHEN** ffprobe reports at least two source channels
- **THEN** the converted upload preserves two channels
