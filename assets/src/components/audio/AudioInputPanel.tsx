import { useCallback, useEffect, useRef, useState } from "react";
import { AudioLines, Users } from "lucide-react";
import type { LanguageOption } from "@/api/types";
import { Dropzone } from "@/components/audio/Dropzone";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { FileChip } from "@/components/audio/FileChip";
import { RecordControls } from "@/components/audio/RecordControls";
import { Waveform } from "@/components/audio/Waveform";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useWaveform } from "@/hooks/useWaveform";

const AUDIO_EXTENSIONS = ["wav", "mp3", "webm", "ogg", "m4a", "mp4", "mpeg", "mpga"];

function isAudioFile(file: File): boolean {
  if (file.type.startsWith("audio/") || file.type === "video/webm") {
    return true;
  }
  const extension = file.name.split(".").pop()?.toLowerCase();
  return AUDIO_EXTENSIONS.includes(extension ?? "");
}

type AudioInputPanelProps = {
  disabled?: boolean;
  isRunning?: boolean;
  batchProgress?: { current: number; total: number } | null;
  language: string;
  languages: LanguageOption[];
  diarizationEnabled: boolean;
  onLanguageChange: (value: string) => void;
  onDiarizationChange: (value: boolean) => void;
  onSubmit: (files: File[]) => void;
  onCancel?: () => void;
  onError: (message: string) => void;
};

export function AudioInputPanel({
  disabled,
  isRunning,
  batchProgress,
  language,
  languages,
  diarizationEnabled,
  onLanguageChange,
  onDiarizationChange,
  onSubmit,
  onCancel,
  onError,
}: AudioInputPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { canvasRef, drawFile, clear, hasWaveform } = useWaveform();

  const syncFiles = useCallback(
    (nextFiles: File[]) => {
      setFiles(nextFiles);
      if (nextFiles.length === 1 && nextFiles[0]) {
        void drawFile(nextFiles[0]);
        setPreviewUrl((prev) => {
          if (prev) {
            URL.revokeObjectURL(prev);
          }
          return URL.createObjectURL(nextFiles[0]!);
        });
      } else {
        clear();
        setPreviewUrl((prev) => {
          if (prev) {
            URL.revokeObjectURL(prev);
          }
          return null;
        });
      }
    },
    [clear, drawFile],
  );

  const recorder = useAudioRecorder({
    onComplete: (file) => syncFiles([file]),
    onError,
  });

  useEffect(
    () => () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    },
    [previewUrl],
  );

  const handleBrowse = () => fileInputRef.current?.click();

  const handleFileInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []).filter(isAudioFile);
    if (selected.length === 0) {
      onError("Unsupported audio format. Use WAV, MP3, WebM, OGG, or M4A.");
      return;
    }
    syncFiles(selected);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragActive(false);
    if (disabled) {
      return;
    }
    const dropped = Array.from(event.dataTransfer.files).filter(isAudioFile);
    if (dropped.length === 0) {
      onError("Unsupported audio format. Use WAV, MP3, WebM, OGG, or M4A.");
      return;
    }
    syncFiles(dropped);
  };

  const removeFile = (index: number) => {
    syncFiles(files.filter((_, i) => i !== index));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (files.length === 0) {
      onError("Please select an audio file");
      return;
    }
    onSubmit(files);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) {
          setDragActive(true);
        }
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={handleDrop}
    >
      <Dropzone active={dragActive} disabled={disabled} onBrowse={handleBrowse}>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.webm,.ogg,.m4a"
          multiple
          className="hidden"
          onChange={handleFileInput}
          disabled={disabled}
        />
      </Dropzone>

      {files.length > 0 ? (
        <div className="space-y-2">
          {files.map((file, index) => (
            <FileChip
              key={`${file.name}-${file.size}-${index}`}
              file={file}
              onRemove={() => removeFile(index)}
              disabled={disabled}
            />
          ))}
        </div>
      ) : null}

      {previewUrl && files.length === 1 ? (
        <div className="space-y-3">
          <Waveform canvasRef={canvasRef} visible={hasWaveform} />
          <AudioPlayer src={previewUrl} disabled={disabled} />
        </div>
      ) : (
        <Waveform canvasRef={canvasRef} visible={hasWaveform} />
      )}

      <RecordControls
        isRecording={recorder.isRecording}
        elapsedSec={recorder.elapsedSec}
        level={recorder.level}
        maxDurationSec={recorder.maxDurationSec}
        disabled={disabled}
        onStart={() => void recorder.start()}
        onStop={recorder.stop}
        onDiscard={recorder.discard}
      />

      <div className="space-y-4 border-t border-zinc-800 pt-5">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(17rem,0.8fr)]">
          <div>
            <label className="block max-w-md space-y-2">
              <span className="text-sm font-medium text-zinc-300">Language</span>
              <Select
                value={language || "auto"}
                onValueChange={(value) =>
                  onLanguageChange(value === "auto" ? "" : value)
                }
                disabled={disabled}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Auto-detect" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto-detect</SelectItem>
                  {languages.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <p className="mt-2 text-xs text-zinc-500">
              Leave as Auto-detect unless you know the spoken language.
            </p>
          </div>

          <label className="flex min-h-20 cursor-pointer items-center justify-between gap-4 rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3 transition-colors hover:border-zinc-700">
            <span className="flex min-w-0 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-300">
                <Users className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-zinc-200">
                  Speaker diarization
                </span>
                <span className="mt-1 block text-xs text-zinc-500">
                  Label speakers on supported providers.
                </span>
              </span>
            </span>
            <input
              type="checkbox"
              checked={diarizationEnabled}
              onChange={(event) => onDiarizationChange(event.target.checked)}
              disabled={disabled}
              className="sr-only peer"
            />
            <span className="relative h-6 w-11 shrink-0 rounded-full bg-zinc-800 ring-1 ring-inset ring-zinc-700 transition-colors after:absolute after:left-0.5 after:top-1/2 after:h-5 after:w-5 after:-translate-y-1/2 after:rounded-full after:bg-zinc-200 after:transition-transform peer-checked:bg-emerald-500/80 peer-checked:ring-emerald-500/60 peer-checked:after:translate-x-5 peer-focus-visible:ring-2 peer-focus-visible:ring-emerald-500/50 peer-disabled:opacity-50" />
          </label>
        </div>

        <div className="border-t border-zinc-800 pt-4">
          <div className="flex flex-col gap-2">
            <Button
              type="submit"
              disabled={disabled || files.length === 0}
              className="h-13 w-full px-6 text-base font-semibold shadow-[0_0_0_1px_rgba(52,211,153,0.18),0_12px_28px_rgba(16,185,129,0.14)] disabled:bg-emerald-900/60 disabled:text-emerald-50/60 disabled:opacity-80"
            >
              <AudioLines className="h-5 w-5" aria-hidden="true" />
              Transcribe audio
            </Button>
            {isRunning && onCancel ? (
              <Button type="button" variant="secondary" onClick={onCancel}>
                Cancel
              </Button>
            ) : null}
            {batchProgress ? (
              <span className="text-sm text-zinc-400">
                File {batchProgress.current} of {batchProgress.total}
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {isRunning && batchProgress ? (
        <Progress
          value={Math.round((batchProgress.current / batchProgress.total) * 100)}
        />
      ) : null}
    </form>
  );
}
