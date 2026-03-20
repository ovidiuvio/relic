<script>
  import { onMount, onDestroy } from 'svelte';

  export let processed;

  let wavesurfer = null;
  let containerRef;
  let loading = true;
  let error = null;
  let isPlaying = false;
  let currentTime = '0:00';
  let totalTime = '0:00';
  let volume = 1;
  let playbackRate = 1;
  let sampleRate = null;
  let numChannels = null;

  // Format seconds into m:ss
  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  onMount(async () => {
    if (!processed || !processed.url) {
      error = "Invalid audio content provided";
      loading = false;
      return;
    }

    try {
      // Import Wavesurfer dynamically via CDN
      const WaveSurferModule = await import('https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js');
      const WaveSurfer = WaveSurferModule.default;

      if (!containerRef) return;

      wavesurfer = WaveSurfer.create({
        container: containerRef,
        waveColor: '#9ca3af', // gray-400
        progressColor: '#2563eb', // blue-600
        cursorColor: '#1d4ed8', // blue-700
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        height: 128,
        normalize: true,
      });

      // Load the blob URL
      wavesurfer.load(processed.url);

      // Event listeners
      wavesurfer.on('ready', () => {
        loading = false;
        totalTime = formatTime(wavesurfer.getDuration());

        const decodedData = wavesurfer.getDecodedData();
        if (decodedData) {
          sampleRate = decodedData.sampleRate;
          numChannels = decodedData.numberOfChannels;
        }
      });

      wavesurfer.on('play', () => isPlaying = true);
      wavesurfer.on('pause', () => isPlaying = false);
      wavesurfer.on('audioprocess', (time) => {
        currentTime = formatTime(time);
      });
      wavesurfer.on('seek', () => {
        currentTime = formatTime(wavesurfer.getCurrentTime());
      });
      wavesurfer.on('error', (err) => {
        console.error("Wavesurfer error:", err);
        error = "Failed to load audio visualization.";
        loading = false;
      });

    } catch (e) {
      console.error("Failed to initialize Wavesurfer:", e);
      error = "Failed to load audio viewer dependency.";
      loading = false;
    }
  });

  onDestroy(() => {
    if (wavesurfer) {
      wavesurfer.destroy();
    }
    if (processed && processed.url) {
      URL.revokeObjectURL(processed.url);
    }
  });

  function togglePlay() {
    if (wavesurfer) {
      wavesurfer.playPause();
    }
  }

  function skipBackward() {
    if (wavesurfer) {
      wavesurfer.skip(-10);
    }
  }

  function skipForward() {
    if (wavesurfer) {
      wavesurfer.skip(10);
    }
  }

  function updateVolume(e) {
    if (wavesurfer) {
      wavesurfer.setVolume(e.target.value);
    }
  }

  function setSpeed(speed) {
    if (wavesurfer) {
      playbackRate = speed;
      wavesurfer.setPlaybackRate(speed);
    }
  }
</script>

<div class="border-t border-gray-200 bg-gray-50 flex flex-col items-stretch">
  <!-- Top header for metadata -->
  <div class="px-6 py-3 border-b border-gray-200 bg-white flex justify-between items-center text-sm">
    <div class="flex items-center space-x-4">
      <span class="font-medium text-gray-700"><i class="fas fa-file-audio mr-2 text-gray-400"></i>Audio Format</span>
      <span class="text-gray-500">{processed.metadata?.mimeType || 'Unknown'}</span>
      {#if sampleRate}
        <span class="text-gray-300">|</span>
        <span class="text-gray-500">{Math.round(sampleRate / 1000)} kHz</span>
      {/if}
      {#if numChannels}
        <span class="text-gray-300">|</span>
        <span class="text-gray-500">{numChannels === 1 ? 'Mono' : numChannels === 2 ? 'Stereo' : `${numChannels} Channels`}</span>
      {/if}
    </div>
    <div class="flex items-center space-x-4">
      {#if !loading && !error}
        <span class="text-gray-500" title="Duration"><i class="fas fa-clock mr-1.5"></i>{totalTime}</span>
      {/if}
    </div>
  </div>

  <div class="p-8">
    {#if error}
      <div class="text-center py-12">
        <i class="fas fa-exclamation-triangle text-amber-400 text-4xl mb-4"></i>
        <p class="text-gray-600 font-medium mb-1">Could not render this audio</p>
        <p class="text-sm text-gray-500">{error}</p>
        <!-- Fallback standard audio player -->
        <audio controls class="mt-6 mx-auto w-full max-w-md" src={processed.url}></audio>
      </div>
    {:else}
      <!-- Visualization Container -->
      <div class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm mb-6 relative">
        {#if loading}
          <div class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-80 z-10 rounded-lg">
            <div class="flex flex-col items-center">
              <i class="fas fa-spinner fa-spin text-blue-600 text-2xl mb-2"></i>
              <span class="text-sm text-gray-500">Analyzing audio...</span>
            </div>
          </div>
        {/if}
        <div bind:this={containerRef} class="w-full h-32"></div>

        <div class="mt-4 flex justify-between text-xs text-gray-500 font-medium">
          <span>{currentTime}</span>
          <span>{totalTime}</span>
        </div>
      </div>

      <!-- Controls -->
      <div class="flex flex-wrap items-center justify-between gap-4 bg-white border border-gray-200 rounded-lg p-4 shadow-sm">

        <!-- Playback Controls -->
        <div class="flex items-center space-x-2">
          <button
            class="maas-btn-secondary w-10 h-10 rounded-full flex items-center justify-center"
            on:click={skipBackward}
            title="Skip back 10s"
            disabled={loading}
          >
            <i class="fas fa-backward-step text-sm"></i>
          </button>

          <button
            class="w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center shadow focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors disabled:opacity-50"
            on:click={togglePlay}
            title={isPlaying ? "Pause" : "Play"}
            disabled={loading}
          >
            <i class="fas {isPlaying ? 'fa-pause' : 'fa-play'} {isPlaying ? '' : 'ml-1'} text-lg"></i>
          </button>

          <button
            class="maas-btn-secondary w-10 h-10 rounded-full flex items-center justify-center"
            on:click={skipForward}
            title="Skip forward 10s"
            disabled={loading}
          >
            <i class="fas fa-forward-step text-sm"></i>
          </button>
        </div>

        <!-- Volume Control -->
        <div class="flex items-center space-x-3 w-48">
          <i class="fas {volume == 0 ? 'fa-volume-xmark text-gray-400' : 'fa-volume-high text-gray-600'}"></i>
          <input
            type="range"
            min="0" max="1" step="0.05"
            bind:value={volume}
            on:input={updateVolume}
            disabled={loading}
            class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          >
        </div>

        <!-- Speed Control -->
        <div class="flex items-center">
          <div class="inline-flex rounded-md shadow-sm" role="group">
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-l-lg hover:bg-gray-50 focus:z-10 focus:ring-2 focus:ring-blue-500 transition-colors {playbackRate === 0.5 ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-white text-gray-700'}"
              on:click={() => setSpeed(0.5)}
              disabled={loading}
            >
              0.5x
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium border-t border-b border-gray-200 hover:bg-gray-50 focus:z-10 focus:ring-2 focus:ring-blue-500 transition-colors {playbackRate === 1 ? 'bg-blue-50 text-blue-700 border-b-blue-200 border-t-blue-200' : 'bg-white text-gray-700'}"
              on:click={() => setSpeed(1)}
              disabled={loading}
            >
              1x
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-r-lg hover:bg-gray-50 focus:z-10 focus:ring-2 focus:ring-blue-500 transition-colors {playbackRate === 1.5 ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-white text-gray-700'}"
              on:click={() => setSpeed(1.5)}
              disabled={loading}
            >
              1.5x
            </button>
          </div>
        </div>

      </div>
    {/if}
  </div>
</div>
