import { useEffect, useRef } from "react";
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
    <div className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
      <div className="flex flex-wrap items-center gap-3">
        {!isRecording ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onStart}
            disabled={disabled}
          >
            Record
          </Button>
        ) : (
          <>
            <Button type="button" variant="destructive" onClick={onStop}>
              Stop
            </Button>
            <Button type="button" variant="ghost" onClick={onDiscard}>
              Discard
            </Button>
            <span className="flex items-center gap-2 text-sm text-red-400">
              <span className="h-2 w-2 rounded-full bg-red-500 record-pulse" />
              {formatDuration(elapsedSec)}
            </span>
          </>
        )}
      </div>

      {isRecording ? (
        <div className="space-y-2">
          <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
            <div
              ref={meterRef}
              className="h-full bg-emerald-500 transition-[width] duration-75"
            />
          </div>
          {nearLimit ? (
            <p className="text-xs text-amber-400">
              Approaching {formatDuration(maxDurationSec)} maximum duration.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
