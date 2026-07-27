/** API types + helpers for the procurement agent UI. */

export type Health = {
  status: string;
  service: string;
  llm_provider: string;
  llm_model: string;
  finops_mode: string;
};

export type TraceEvent = {
  kind?: string;
  node?: string;
  message?: string;
  data?: Record<string, unknown>;
};

export type EmailDraft = {
  vendor?: string;
  subject?: string;
  body?: string;
  intent?: string;
};

export type RunState = {
  goal?: string;
  sku?: string | null;
  quantity?: number | null;
  invoice_id?: string | null;
  vendors?: Record<string, unknown>[];
  historical_price?: number | null;
  contract_price?: number | null;
  best_vendor?: string | null;
  best_price?: number | null;
  negotiate_vendor?: string | null;
  negotiate_price?: number | null;
  email_draft?: EmailDraft | null;
  hitl_status?: string | null;
  hitl_decision?: string | null;
  outbox_path?: string | null;
  summary?: string | null;
  error?: string | null;
  search_attempts?: number;
  replan_done?: boolean;
  suggested_sku?: string | null;
  original_sku?: string | null;
  review_result?: Record<string, unknown> | null;
  finops_degraded?: boolean;
  messages?: string[];
  trace?: TraceEvent[];
};

export type RunInterrupt = {
  type?: string;
  prompt?: string;
  actions?: string[];
  draft?: EmailDraft;
  vendor?: string;
  sku?: string;
  goal?: string;
  value?: unknown;
};

export type RunSnapshot = {
  run_id: string;
  goal: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  summary?: string | null;
  interrupt?: RunInterrupt | null;
  state?: RunState;
};

export type StreamEvent =
  | { type: "status"; run_id?: string; status?: string; goal?: string; decision?: string; replay?: boolean }
  | { type: "node"; run_id?: string; node?: string }
  | {
      type: "trace";
      run_id?: string;
      kind?: string;
      node?: string;
      message?: string;
      data?: Record<string, unknown>;
      replay?: boolean;
    }
  | { type: "interrupt"; run_id?: string; interrupt?: RunInterrupt; replay?: boolean }
  | ({ type: "done" } & Partial<RunSnapshot> & { replay?: boolean })
  | { type: "error"; run_id?: string; error?: string };

export async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
  return res.json();
}

async function* readSse(res: Response): AsyncGenerator<StreamEvent> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (!res.body) throw new Error("No response body for SSE");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice("data:".length).trim();
      if (!payload) continue;
      yield JSON.parse(payload) as StreamEvent;
    }
  }
}

export async function* streamCreateRun(goal: string): AsyncGenerator<StreamEvent> {
  const res = await fetch("/api/runs/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
  yield* readSse(res);
}

export async function* streamResumeRun(
  runId: string,
  decision: "approve" | "edit" | "reject",
  editedDraft?: string,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`/api/runs/${runId}/resume/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      decision,
      edited_draft: editedDraft,
    }),
  });
  yield* readSse(res);
}

export const DEMO_GOAL =
  "Find a cost-effective vendor for 500 units of SKU-1001 and draft a negotiation email.";
