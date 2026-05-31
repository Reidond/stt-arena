import { Check, ChevronDown, ChevronUp, Copy } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import type { TranscriptionResult } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatLatency, providerInitials } from "@/lib/format";
import { copyText as writeClipboardText, getResultCost } from "@/lib/export";

const COLUMN_COUNT = 6;

type SortKey =
  | "provider"
  | "latency_ms"
  | "word_count"
  | "confidence"
  | "cost"
  | "status";

type ResultTableProps = {
  results: TranscriptionResult[];
};

function sortValue(result: TranscriptionResult, key: SortKey): string | number {
  switch (key) {
    case "provider":
      return result.display_name ?? result.provider_id;
    case "latency_ms":
      return result.latency_ms;
    case "word_count":
      return result.word_count ?? -1;
    case "confidence":
      return result.confidence ?? -1;
    case "cost":
      return getResultCost(result);
    case "status":
      return result.status;
    default:
      return 0;
  }
}

function SortHeader({
  label,
  sortKey,
  activeKey,
  ascending,
  onSort,
  className,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  ascending: boolean;
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  const active = activeKey === sortKey;
  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className={cn(
        "inline-flex items-center gap-1 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 transition hover:text-zinc-300",
        active && "text-zinc-300",
        className,
      )}
    >
      {label}
      <span className="text-[10px] text-zinc-600">
        {active ? (ascending ? "↑" : "↓") : ""}
      </span>
    </button>
  );
}

function resultTranscript(result: TranscriptionResult): string | null {
  const content = result.status === "ok" ? result.text : result.error;
  return content?.trim() ? content : null;
}

function TranscriptDetailPanel({
  result,
  onClose,
}: {
  result: TranscriptionResult;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const name = result.display_name ?? result.provider_id;
  const isOk = result.status === "ok";
  const content = isOk ? result.text : result.error;

  const copyText = async () => {
    if (!content) {
      return;
    }
    if (await writeClipboardText(content)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  };

  if (!content) {
    return null;
  }

  return (
    <div className="border-t border-zinc-800/80 bg-zinc-900/50 px-4 py-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-zinc-200">{name}</span>
          <span className="text-xs text-zinc-500">full transcript</span>
        </div>
        <div className="flex items-center gap-2">
          {isOk ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => void copyText()}
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy
                </>
              )}
            </Button>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 text-xs text-zinc-500"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-950/80 px-4 py-3">
        <p
          className={cn(
            "whitespace-pre-wrap text-sm leading-relaxed",
            isOk ? "text-zinc-200" : "text-red-300",
          )}
        >
          {content}
        </p>
      </div>
    </div>
  );
}

export function ResultTable({ results }: ResultTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("latency_ms");
  const [ascending, setAscending] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...results].sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      if (typeof av === "string" && typeof bv === "string") {
        return ascending ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return ascending
        ? Number(av) - Number(bv)
        : Number(bv) - Number(av);
    });
  }, [ascending, results, sortKey]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setAscending((value) => !value);
      return;
    }
    setSortKey(key);
    setAscending(key === "provider" || key === "status");
  };

  const toggleExpanded = (providerId: string) => {
    setExpandedId((current) => (current === providerId ? null : providerId));
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/40">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/80">
              <th className="px-4 py-3 text-left align-bottom">
                <SortHeader
                  label="Provider"
                  sortKey="provider"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
              <th className="px-3 py-3 text-left align-bottom">
                <SortHeader
                  label="Status"
                  sortKey="status"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
              <th className="px-2 py-3 text-left align-bottom">
                <SortHeader
                  label="Latency"
                  sortKey="latency_ms"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
              <th className="px-2 py-3 text-left align-bottom">
                <SortHeader
                  label="Words"
                  sortKey="word_count"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
              <th className="px-2 py-3 text-left align-bottom">
                <SortHeader
                  label="Conf."
                  sortKey="confidence"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
              <th className="px-3 py-3 text-left align-bottom">
                <SortHeader
                  label="Cost"
                  sortKey="cost"
                  activeKey={sortKey}
                  ascending={ascending}
                  onSort={toggleSort}
                />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((result, index) => {
              const name = result.display_name ?? result.provider_id;
              const isOk = result.status === "ok";
              const isExpanded = expandedId === result.provider_id;
              const transcript = resultTranscript(result);
              const hasTranscript = transcript !== null;

              return (
                <Fragment key={result.provider_id}>
                  <tr
                    className={cn(
                      "border-b border-zinc-800/70 transition-colors",
                      index % 2 === 1 && "bg-zinc-950/30",
                      isExpanded && "border-b-0 bg-zinc-900/40",
                      hasTranscript &&
                        "cursor-pointer hover:bg-zinc-900/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 focus-visible:ring-inset",
                    )}
                    onClick={() => {
                      if (hasTranscript) {
                        toggleExpanded(result.provider_id);
                      }
                    }}
                    onKeyDown={(event) => {
                      if (!hasTranscript) {
                        return;
                      }
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        toggleExpanded(result.provider_id);
                      }
                    }}
                    tabIndex={hasTranscript ? 0 : undefined}
                    role={hasTranscript ? "button" : undefined}
                    aria-expanded={hasTranscript ? isExpanded : undefined}
                    aria-label={
                      hasTranscript
                        ? `${isExpanded ? "Hide" : "Show"} transcript for ${name}`
                        : undefined
                    }
                  >
                    <td className="px-4 py-3 align-middle">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                          {hasTranscript ? (
                            isExpanded ? (
                              <ChevronUp
                                className="h-4 w-4 text-emerald-400"
                                aria-hidden="true"
                              />
                            ) : (
                              <ChevronDown
                                className="h-4 w-4 text-zinc-500"
                                aria-hidden="true"
                              />
                            )
                          ) : null}
                        </span>
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-semibold text-emerald-300">
                          {providerInitials(name)}
                        </span>
                        <span className="truncate font-medium text-zinc-100">
                          {name}
                        </span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 align-middle">
                      <Badge variant={isOk ? "success" : "error"}>
                        {isOk ? "ok" : "error"}
                      </Badge>
                    </td>
                    <td className="whitespace-nowrap px-2 py-3 align-middle font-mono text-xs tabular-nums text-zinc-300">
                      {formatLatency(result.latency_ms)}
                    </td>
                    <td className="whitespace-nowrap px-2 py-3 align-middle font-mono text-xs tabular-nums text-zinc-300">
                      {result.word_count ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-2 py-3 align-middle font-mono text-xs tabular-nums text-zinc-300">
                      {result.confidence != null
                        ? `${Math.round(result.confidence * 100)}%`
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 align-middle font-mono text-xs tabular-nums text-zinc-300">
                      {getResultCost(result) > 0
                        ? `$${getResultCost(result).toFixed(4)}`
                        : "—"}
                    </td>
                  </tr>
                  {isExpanded ? (
                    <tr className="border-b border-zinc-800/70">
                      <td colSpan={COLUMN_COUNT} className="p-0">
                        <TranscriptDetailPanel
                          result={result}
                          onClose={() => setExpandedId(null)}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
