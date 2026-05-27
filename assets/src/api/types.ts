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

export type TranscriptionResult = {
  provider_id: string;
  display_name?: string;
  status: "ok" | "error" | string;
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
  results: TranscriptionResult[];
};

export type ProviderBilling = {
  plan_label: string;
  rate_usd_per_minute: number;
  free_minutes_monthly: number;
};

export type ProviderStatus = {
  id: string;
  display_name: string;
  enabled: boolean;
  available: boolean;
  reason?: string | null;
  billing?: ProviderBilling | null;
};

export type LanguageOption = {
  code: string;
  label: string;
};

export type ProgressiveSession = {
  session_id: string;
  audio_duration_sec: number;
  providers: Array<{ id: string; display_name: string }>;
};

export type ProviderRunStatus =
  | { state: "pending" }
  | { state: "running" }
  | { state: "done"; result: TranscriptionResult }
  | { state: "error"; message: string };

export type BatchRun = {
  id: string;
  fileName: string;
  audioDurationSec: number;
  providers: Array<{ id: string; display_name: string }>;
  providerStatus: Record<string, ProviderRunStatus>;
  results: TranscriptionResult[];
  isComplete: boolean;
  error?: string;
};
