export type CostBreakdown = {
  usd: number;
  plan_id: string;
  plan_label: string;
  model: string;
  billing_mode: string;
  audio_duration_sec: number;
  billable_duration_sec: number;
  rate_usd_per_minute: number;
  free_minutes_applied: number;
  monthly_minutes_used: number;
  pricing_url: string;
  notes: string;
};

export type ExportResult = {
  provider_id: string;
  display_name?: string;
  status: string;
  text: string | null;
  latency_ms: number;
  word_count: number | null;
  confidence: number | null;
  error: string | null;
  estimated_cost_usd?: number | null;
  cost?: CostBreakdown | null;
};

export type ExportPayload = {
  audio_duration_sec: number;
  results: ExportResult[];
};

function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadJson(payload: ExportPayload): void {
  const body = JSON.stringify(payload, null, 2);
  downloadBlob(
    `stt-arena-${Date.now()}.json`,
    new Blob([body], { type: "application/json" }),
  );
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}

export function downloadCsv(payload: ExportPayload): void {
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
  const body = [headers.join(","), ...rows].join("\n");
  downloadBlob(
    `stt-arena-${Date.now()}.csv`,
    new Blob([body], { type: "text/csv" }),
  );
}

function sumCosts(results: ExportResult[]): number {
  return results.reduce((total, result) => {
    const value = result.cost?.usd ?? result.estimated_cost_usd ?? 0;
    return total + value;
  }, 0);
}

export function formatTotalCost(results: ExportResult[]): string {
  return `$${sumCosts(results).toFixed(4)}`;
}
