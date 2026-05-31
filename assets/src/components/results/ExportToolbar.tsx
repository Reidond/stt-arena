import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  Check,
  CircleAlert,
  Copy,
  Download,
  FileJson,
  TableProperties,
  TextSelect,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ExportPayload } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  copyJson,
  copyText,
  csvExportBody,
  downloadCsv,
  downloadJson,
  formatTotalCost,
  jsonExportBody,
} from "@/lib/export";

type ExportToolbarProps = {
  payload: ExportPayload;
};

type ExportFormat = "json" | "csv";

export function ExportToolbar({ payload }: ExportToolbarProps) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">(
    "idle",
  );
  const [previewFormat, setPreviewFormat] = useState<ExportFormat | null>(null);
  const previewRef = useRef<HTMLTextAreaElement>(null);
  const previewBody = useMemo(() => {
    if (previewFormat === "csv") {
      return csvExportBody(payload);
    }
    return jsonExportBody(payload);
  }, [payload, previewFormat]);

  const selectPreview = () => {
    previewRef.current?.focus();
    previewRef.current?.select();
  };

  const openPreview = (format: ExportFormat) => {
    setPreviewFormat(format);
  };

  useEffect(() => {
    if (previewFormat !== null && copyStatus === "failed") {
      const timer = window.setTimeout(selectPreview);
      return () => window.clearTimeout(timer);
    }
  }, [copyStatus, previewFormat]);

  const handleCopy = async () => {
    if (await copyJson(payload)) {
      setCopyStatus("copied");
    } else {
      setCopyStatus("failed");
      openPreview("json");
    }
    window.setTimeout(() => setCopyStatus("idle"), 1500);
  };

  const handlePreviewCopy = async () => {
    if (await copyText(previewBody)) {
      setCopyStatus("copied");
    } else {
      setCopyStatus("failed");
      selectPreview();
    }
    window.setTimeout(() => setCopyStatus("idle"), 1500);
  };

  const handleDownload = () => {
    if (previewFormat === "csv") {
      downloadCsv(payload);
    } else {
      downloadJson(payload);
    }
  };

  return (
    <>
      <div className="sticky top-4 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/95 p-4 backdrop-blur">
        <span className="text-sm text-zinc-400">Export results</span>
        <Button type="button" variant="secondary" size="sm" onClick={() => openPreview("json")}>
          <FileJson className="h-3.5 w-3.5" />
          JSON
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={() => openPreview("csv")}>
          <TableProperties className="h-3.5 w-3.5" />
          CSV
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => void handleCopy()}>
          {copyStatus === "copied" ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copied JSON
            </>
          ) : copyStatus === "failed" ? (
            <>
              <CircleAlert className="h-3.5 w-3.5" />
              Select JSON
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy JSON
            </>
          )}
        </Button>
        <span className="text-sm font-medium text-zinc-200">
          Total: {formatTotalCost(payload.results)}
        </span>
        <span className="text-xs text-zinc-600">Costs use configured billing plans.</span>
      </div>

      <DialogPrimitive.Root
        open={previewFormat !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPreviewFormat(null);
          }
        }}
      >
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/60" />
          <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[min(44rem,90vh)] w-[min(54rem,92vw)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-lg border border-zinc-800 bg-zinc-950 p-5 shadow-xl">
            <div className="flex items-center justify-between gap-3 pr-8">
              <DialogPrimitive.Title className="text-base font-medium text-zinc-100">
                {previewFormat?.toUpperCase()} export
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="sr-only">
                Generated transcription export
              </DialogPrimitive.Description>
            </div>
            {copyStatus === "failed" ? (
              <p className="text-xs text-amber-300">
                Clipboard access is blocked. The export text has been selected.
              </p>
            ) : null}
            <textarea
              ref={previewRef}
              aria-label={`${previewFormat?.toUpperCase()} export text`}
              className="min-h-72 w-full resize-y rounded-md border border-zinc-800 bg-zinc-900 p-3 font-mono text-xs leading-relaxed text-zinc-200 outline-none focus:border-emerald-700"
              readOnly
              value={previewBody}
            />
            <div className="flex flex-wrap justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={selectPreview}>
                <TextSelect className="h-3.5 w-3.5" />
                Select all
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => void handlePreviewCopy()}>
                <Copy className="h-3.5 w-3.5" />
                Copy
              </Button>
              <Button type="button" size="sm" onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
                Download {previewFormat?.toUpperCase()}
              </Button>
            </div>
            <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </DialogPrimitive.Close>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </>
  );
}
