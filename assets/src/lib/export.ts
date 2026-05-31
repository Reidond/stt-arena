import type { ExportPayload, TranscriptionResult } from "../api/types";

function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}

export function jsonExportBody(payload: ExportPayload): string {
  return JSON.stringify(payload, null, 2);
}

export function downloadJson(payload: ExportPayload): void {
  downloadBlob(
    `stt-arena-${Date.now()}.json`,
    new Blob([jsonExportBody(payload)], { type: "application/json" }),
  );
}

export function csvExportBody(payload: ExportPayload): string {
  const headers = [
    "provider_id",
    "display_name",
    "status",
    "text",
    "latency_ms",
    "word_count",
    "confidence",
    "cost_usd",
    "cost_plan",
    "cost_billable_duration_sec",
    "cost_rate_usd_per_minute",
    "error",
  ];
  const rows = payload.results.map((result) =>
    [
      result.provider_id,
      result.display_name ?? "",
      result.status,
      result.text ?? "",
      String(result.latency_ms),
      result.word_count ?? "",
      result.confidence ?? "",
      result.cost?.usd ?? result.estimated_cost_usd ?? "",
      result.cost?.plan_label ?? "",
      result.cost?.billable_duration_sec ?? "",
      result.cost?.rate_usd_per_minute ?? "",
      result.error ?? "",
    ]
      .map((cell) => csvEscape(String(cell)))
      .join(","),
  );
  return [headers.join(","), ...rows].join("\n");
}

export function downloadCsv(payload: ExportPayload): void {
  downloadBlob(
    `stt-arena-${Date.now()}.csv`,
    new Blob([csvExportBody(payload)], { type: "text/csv" }),
  );
}

export async function copyJson(payload: ExportPayload): Promise<boolean> {
  return copyText(jsonExportBody(payload));
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    textArea.style.pointerEvents = "none";
    document.body.append(textArea);
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);
    const copied = document.execCommand("copy");
    textArea.remove();
    return copied;
  }
}

function sumCosts(results: TranscriptionResult[]): number {
  return results.reduce((total, result) => {
    const value = result.cost?.usd ?? result.estimated_cost_usd ?? 0;
    return total + value;
  }, 0);
}

export function formatTotalCost(results: TranscriptionResult[]): string {
  return `$${sumCosts(results).toFixed(4)}`;
}

export function getResultCost(result: TranscriptionResult): number {
  return result.cost?.usd ?? result.estimated_cost_usd ?? 0;
}
