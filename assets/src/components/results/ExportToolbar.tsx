import { useState } from "react";
import type { ExportPayload } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  copyJson,
  downloadCsv,
  downloadJson,
  formatTotalCost,
} from "@/lib/export";

type ExportToolbarProps = {
  payload: ExportPayload;
};

export function ExportToolbar({ payload }: ExportToolbarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await copyJson(payload);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="sticky top-4 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/95 p-4 backdrop-blur">
      <span className="text-sm text-zinc-400">Export results</span>
      <Button type="button" variant="secondary" size="sm" onClick={() => downloadJson(payload)}>
        JSON
      </Button>
      <Button type="button" variant="secondary" size="sm" onClick={() => downloadCsv(payload)}>
        CSV
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={() => void handleCopy()}>
        {copied ? "Copied JSON" : "Copy JSON"}
      </Button>
      <span className="text-sm font-medium text-zinc-200">
        Total: {formatTotalCost(payload.results)}
      </span>
      <span className="text-xs text-zinc-600">Costs use configured billing plans.</span>
    </div>
  );
}
