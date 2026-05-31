import { Check, Copy, Loader2 } from "lucide-react";
import { useState } from "react";
import type { TranscriptionResult } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { errorHint } from "@/lib/diff";
import { formatLatency, providerInitials } from "@/lib/format";
import { copyText as writeClipboardText, getResultCost } from "@/lib/export";

type ResultCardProps = {
  result?: TranscriptionResult;
  providerName?: string;
  loading?: boolean;
  badges?: string[];
};

export function ResultCard({
  result,
  providerName,
  loading,
  badges = [],
}: ResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (loading) {
    return (
      <Card className="masonry-item">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <CardTitle>{providerName ?? "Provider"}</CardTitle>
              <p className="text-xs text-zinc-500">transcribing…</p>
            </div>
            <Loader2 className="h-5 w-5 animate-spin text-emerald-400" />
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-4/6" />
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return null;
  }

  const name = result.display_name ?? result.provider_id;
  const isError = result.status !== "ok";
  const text = result.text ?? "";
  const isLong = text.length > 420;
  const hint = errorHint(result.error);

  const copyText = async () => {
    if (!text) {
      return;
    }
    if (await writeClipboardText(text)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <Card
      className={`masonry-item card-enter ${
        isError ? "border-red-900/60 bg-red-950/20" : ""
      }`}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-emerald-300">
              {providerInitials(name)}
            </div>
            <div>
              <CardTitle>{name}</CardTitle>
              <div className="mt-1 flex flex-wrap gap-1">
                <Badge variant={isError ? "error" : "success"}>
                  {isError ? "error" : "success"}
                </Badge>
                {badges.map((badge) => (
                  <Badge key={badge} variant="success">
                    {badge}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <span className="rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-300">
            {formatLatency(result.latency_ms)}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="space-y-2">
            <p className="text-sm text-red-300">
              {result.error ?? "Transcription failed"}
            </p>
            {hint ? <p className="text-xs text-zinc-500">{hint}</p> : null}
          </div>
        ) : (
          <>
            <p
              className={`whitespace-pre-wrap text-sm leading-relaxed text-zinc-200 ${
                !expanded && isLong ? "line-clamp-6" : ""
              }`}
            >
              {text || "—"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {isLong ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setExpanded((value) => !value)}
                >
                  {expanded ? "Show less" : "Show more"}
                </Button>
              ) : null}
              {text ? (
                <Button type="button" variant="ghost" size="sm" onClick={() => void copyText()}>
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
            </div>
            <dl className="mt-4 flex flex-wrap gap-4 text-xs text-zinc-500">
              {result.word_count != null ? (
                <div>
                  <dt className="uppercase tracking-wide">Words</dt>
                  <dd className="text-zinc-300">{result.word_count}</dd>
                </div>
              ) : null}
              {result.confidence != null ? (
                <div>
                  <dt className="uppercase tracking-wide">Confidence</dt>
                  <dd className="text-zinc-300">
                    {Math.round(result.confidence * 100)}%
                  </dd>
                </div>
              ) : null}
              {getResultCost(result) > 0 ? (
                <div>
                  <dt className="uppercase tracking-wide">Cost</dt>
                  <dd className="text-zinc-300">${getResultCost(result).toFixed(4)}</dd>
                </div>
              ) : null}
              {result.cost ? (
                <>
                  <div>
                    <dt className="uppercase tracking-wide">Plan</dt>
                    <dd className="text-zinc-300">{result.cost.plan_label}</dd>
                  </div>
                  <div>
                    <dt className="uppercase tracking-wide">Billable</dt>
                    <dd className="text-zinc-300">
                      {result.cost.billable_duration_sec}s
                    </dd>
                  </div>
                </>
              ) : null}
            </dl>
          </>
        )}
      </CardContent>
    </Card>
  );
}
