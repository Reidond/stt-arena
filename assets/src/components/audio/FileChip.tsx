import { X } from "lucide-react";
import { formatFileSize } from "@/lib/format";
import { Button } from "@/components/ui/button";

type FileChipProps = {
  file: File;
  onRemove: () => void;
  disabled?: boolean;
};

export function FileChip({ file, onRemove, disabled }: FileChipProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-zinc-200">{file.name}</p>
        <p className="text-xs text-zinc-500">{formatFileSize(file.size)}</p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 shrink-0"
        onClick={onRemove}
        disabled={disabled}
        aria-label={`Remove ${file.name}`}
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
