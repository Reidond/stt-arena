import { useCallback, useEffect, useRef, useState } from "react";

const BAR_COUNT = 120;

export function useWaveform() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hasWaveform, setHasWaveform] = useState(false);

  const clear = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    context?.clearRect(0, 0, canvas.width, canvas.height);
    setHasWaveform(false);
  }, []);

  const drawFile = useCallback(async (file: File) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    const displayWidth = canvas.clientWidth || 800;
    const displayHeight = canvas.clientHeight || 80;
    const centerY = displayHeight / 2;
    canvas.width = Math.floor(displayWidth * dpr);
    canvas.height = Math.floor(displayHeight * dpr);

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, displayWidth, displayHeight);
    setHasWaveform(true);

    const buffer = await file.arrayBuffer();
    const audioContext = new AudioContext();
    try {
      const audioBuffer = await audioContext.decodeAudioData(buffer.slice(0));
      const channel = audioBuffer.getChannelData(0);
      const blockSize = Math.max(1, Math.floor(channel.length / BAR_COUNT));

      context.fillStyle = "#52525b";
      for (let index = 0; index < BAR_COUNT; index += 1) {
        let peak = 0;
        const start = index * blockSize;
        const end = Math.min(channel.length, start + blockSize);
        for (let sample = start; sample < end; sample += 1) {
          peak = Math.max(peak, Math.abs(channel[sample] ?? 0));
        }
        const barHeight = Math.max(2, peak * displayHeight * 0.9);
        const x = (index / BAR_COUNT) * displayWidth;
        const barWidth = displayWidth / BAR_COUNT - 1;
        context.fillRect(x, centerY - barHeight / 2, barWidth, barHeight);
      }
    } catch {
      context.fillStyle = "#a1a1aa";
      context.font = "12px Geist Sans, system-ui";
      context.fillText("Waveform preview unavailable", 12, centerY);
    } finally {
      await audioContext.close();
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !hasWaveform) {
      return;
    }
    const observer = new ResizeObserver(() => {
      // Redraw handled by parent when file changes; resize keeps canvas sized.
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [hasWaveform]);

  return { canvasRef, drawFile, clear, hasWaveform };
}
