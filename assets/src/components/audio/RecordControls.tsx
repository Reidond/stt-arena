import { useEffect, useRef } from "react";
import { Mic, Square, Trash2, Waves } from "lucide-react";
import { formatDuration } from "@/lib/format";
import { Button } from "@/components/ui/button";

type RecordControlsProps = {
  isRecording: boolean;
  elapsedSec: number;
  level: number;
  maxDurationSec: number;
  disabled?: boolean;
  onStart: () => void;
  onStop: () => void;
  onDiscard: () => void;
};

export function RecordControls({
  isRecording,
  elapsedSec,
  level,
  maxDurationSec,
  disabled,
  onStart,
  onStop,
  onDiscard,
}: RecordControlsProps) {
  const meterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (meterRef.current) {
      meterRef.current.style.width = `${Math.round(level * 100)}%`;
    }
  }, [level]);

  const nearLimit = elapsedSec >= maxDurationSec - 30;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={
              isRecording
                ? "flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-red-500/40 bg-red-950/50 text-red-300"
                : "flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            }
          >
            {isRecording ? (
              <span className="h-3 w-3 rounded-full bg-red-400 record-pulse" />
            ) : (
              <Mic className="h-5 w-5" aria-hidden="true" />
            )}
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <p className="text-sm font-medium text-zinc-100">
                {isRecording ? "Recording microphone" : "Record from microphone"}
              </p>
              <span className="font-mono text-xs text-zinc-500">
                {formatDuration(elapsedSec)} / {formatDuration(maxDurationSec)}
              </span>
            </div>
            <p className="mt-1 text-xs text-zinc-500">
              {isRecording
                ? "Speak clearly, then stop to use the captured audio."
                : "Capture a fresh sample without leaving the page."}
            </p>
          </div>
        </div>

        {!isRecording ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onStart}
            disabled={disabled}
            className="w-full sm:w-auto"
          >
            <Mic className="h-4 w-4" aria-hidden="true" />
            Start recording
          </Button>
        ) : (
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
            <Button type="button" variant="destructive" onClick={onStop}>
              <Square className="h-4 w-4" aria-hidden="true" />
              Stop
            </Button>
            <Button type="button" variant="ghost" onClick={onDiscard}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Discard
            </Button>
          </div>
        )}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-zinc-500">
          <Waves className="h-4 w-4" aria-hidden="true" />
          Level
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
          <div
            ref={meterRef}
            className={
              isRecording
                ? "h-full bg-emerald-400 transition-[width] duration-75"
                : "h-full w-0 bg-zinc-700"
            }
          />
        </div>
      </div>

      {isRecording && nearLimit ? (
        <p className="mt-2 text-xs text-amber-400">
          Approaching {formatDuration(maxDurationSec)} maximum duration.
        </p>
      ) : null}
    </div>
  );
}
