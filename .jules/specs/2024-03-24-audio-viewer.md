# Spec: Audio Viewer
Date: 2024-03-24
Author: lens

## Format
audio/mpeg, audio/wav, audio/ogg, audio/flac, audio/aac, audio/webm, audio/mp3
.mp3, .wav, .ogg, .flac, .aac, .m4a

## Current behavior
Falls through to download prompt.

## What this builds
A native-feeling audio player with a waveform visualization using wavesurfer.js.
It offers play/pause, seek, volume, and playback speed controls. It extracts and shows metadata like duration, channels, and sample rate.

## Processor result shape
{
  type: 'audio',
  url: '[blob url]',
  metadata: { mimeType: 'audio/mpeg' },
  error: null
}

## CDN dependency
Wavesurfer.js (https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js) — provides an easy-to-use, accessible waveform visualization and Web Audio API wrapper that automatically extracts duration and simplifies audio manipulation.

## Files created
- frontend/src/services/processors/audioProcessor.js: Processes raw bytes into a blob URL for the audio element.
- frontend/src/components/renderers/AudioRenderer.svelte: The Svelte component that renders the player and controls.

## Files modified
- frontend/src/services/data/fileTypes.js: Register the audio mime types and extensions.
- frontend/src/services/processors/index.js: Wire up the audioProcessor.
- frontend/src/components/RelicViewer.svelte: Switch case to render AudioRenderer.

## Loading strategy
The Svelte component displays a loading state while Wavesurfer.js is being imported via dynamic import in `onMount` and while it analyzes the audio file to draw the waveform.

## Error handling
If Wavesurfer fails to load or the audio file is corrupted, the component catches the error and displays a standard error state.

## Acceptance criteria
- [ ] MP3, WAV, OGG, FLAC files render a waveform instead of a download prompt.
- [ ] Play, pause, volume, and speed controls work.
- [ ] Waveform visualization reflects the audio track.
- [ ] Metadata (duration) is extracted and displayed in the header strip.
