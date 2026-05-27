const BAR_COUNT = 120;

export function initWaveform(canvasId: string): {
  drawFile: (file: File) => Promise<void>;
  clear: () => void;
} {
  const canvas = document.getElementById(canvasId);
  if (!(canvas instanceof HTMLCanvasElement)) {
    return {
      drawFile: async () => undefined,
      clear: () => undefined,
    };
  }

  const context = canvas.getContext("2d");

  function clear(): void {
    canvas.classList.add("hidden");
    if (!context) {
      return;
    }
    context.clearRect(0, 0, canvas.width, canvas.height);
  }

  async function drawFile(file: File): Promise<void> {
    if (!context) {
      return;
    }

    canvas.classList.remove("hidden");
    context.clearRect(0, 0, canvas.width, canvas.height);

    const buffer = await file.arrayBuffer();
    const audioContext = new AudioContext();
    try {
      const audioBuffer = await audioContext.decodeAudioData(buffer.slice(0));
      const channel = audioBuffer.getChannelData(0);
      const blockSize = Math.max(1, Math.floor(channel.length / BAR_COUNT));
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      context.fillStyle = "#3f3f46";
      for (let index = 0; index < BAR_COUNT; index += 1) {
        let peak = 0;
        const start = index * blockSize;
        const end = Math.min(channel.length, start + blockSize);
        for (let sample = start; sample < end; sample += 1) {
          peak = Math.max(peak, Math.abs(channel[sample] ?? 0));
        }
        const barHeight = Math.max(2, peak * height * 0.9);
        const x = (index / BAR_COUNT) * width;
        const barWidth = width / BAR_COUNT - 1;
        context.fillRect(x, centerY - barHeight / 2, barWidth, barHeight);
      }
    } catch {
      context.fillStyle = "#71717a";
      context.font = "12px system-ui";
      context.fillText("Waveform preview unavailable", 12, height / 2);
    } finally {
      await audioContext.close();
    }
  }

  return { drawFile, clear };
}
