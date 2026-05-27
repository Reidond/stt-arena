type WaveformProps = {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  visible: boolean;
};

export function Waveform({ canvasRef, visible }: WaveformProps) {
  if (!visible) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="mt-4 h-20 w-full rounded-lg bg-zinc-950/80"
      aria-label="Audio waveform preview"
    />
  );
}
