import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";

type AudioPlayerProps = {
  src: string;
  disabled?: boolean;
  className?: string;
};

export function AudioPlayer({ src, disabled, className }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    audio.pause();
    audio.currentTime = 0;
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    audio.load();
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    const onTimeUpdate = () => {
      if (!seeking) {
        setCurrentTime(audio.currentTime);
      }
    };
    const onLoadedMetadata = () => setDuration(audio.duration || 0);
    const onDurationChange = () => setDuration(audio.duration || 0);
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onEnded = () => {
      setPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    audio.addEventListener("durationchange", onDurationChange);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      audio.removeEventListener("durationchange", onDurationChange);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("ended", onEnded);
    };
  }, [seeking, src]);

  const togglePlayback = async () => {
    const audio = audioRef.current;
    if (!audio || disabled) {
      return;
    }
    if (playing) {
      audio.pause();
      return;
    }
    try {
      await audio.play();
    } catch {
      setPlaying(false);
    }
  };

  const handleSeek = (value: number) => {
    setCurrentTime(value);
    const audio = audioRef.current;
    if (audio) {
      audio.currentTime = value;
    }
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-950/80 px-3 py-3",
        className,
      )}
    >
      <audio ref={audioRef} src={src} preload="metadata" className="hidden" />

      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="h-9 w-9 shrink-0 rounded-full"
          onClick={() => void togglePlayback()}
          disabled={disabled || duration === 0}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Play className="h-4 w-4 translate-x-0.5" aria-hidden="true" />
          )}
        </Button>

        <div className="min-w-0 flex-1 space-y-1.5">
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.01}
            value={Math.min(currentTime, duration || 0)}
            disabled={disabled || duration === 0}
            onChange={(event) => handleSeek(Number(event.target.value))}
            onPointerDown={() => setSeeking(true)}
            onPointerUp={() => setSeeking(false)}
            className="audio-player__seek h-1.5 w-full cursor-pointer appearance-none rounded-full bg-zinc-800 accent-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Seek"
            aria-valuemin={0}
            aria-valuemax={duration}
            aria-valuenow={currentTime}
            style={{
              background: `linear-gradient(to right, rgb(16 185 129) ${progress}%, rgb(39 39 42) ${progress}%)`,
            }}
          />
          <div className="flex items-center justify-between gap-2 text-xs tabular-nums text-zinc-500">
            <span>{formatDuration(currentTime)}</span>
            <span>{duration > 0 ? formatDuration(duration) : "0:00"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
