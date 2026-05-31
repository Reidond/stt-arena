import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

type DropzoneProps = {
  active: boolean;
  disabled?: boolean;
  onBrowse: () => void;
  children?: React.ReactNode;
};

export function Dropzone({
  active,
  disabled,
  onBrowse,
  children,
}: DropzoneProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/40 p-6 transition-colors lg:p-8",
        active && "border-emerald-500 bg-emerald-950/20",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-zinc-700 bg-zinc-950">
          <Upload className="h-5 w-5 text-emerald-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-zinc-200">
            Drop audio files here or browse
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            WAV, MP3, WebM, OGG, M4A · max 25 MB · max 15 min each
          </p>
        </div>
        <button
          type="button"
          onClick={onBrowse}
          disabled={disabled}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm font-medium text-zinc-200 transition hover:border-emerald-600 hover:text-emerald-300 disabled:opacity-50"
        >
          Choose files
        </button>
      </div>
      {children}
    </div>
  );
}
