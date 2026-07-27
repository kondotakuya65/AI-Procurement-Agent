"use client";

import type { RunInterrupt, RunState } from "@/lib/api";

type StatePanelProps = {
  runId: string | null;
  status: string | null;
  state: RunState | null;
  interrupt: RunInterrupt | null;
  summary: string | null;
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="grid grid-cols-[7.5rem_1fr] gap-2 py-1.5 text-sm">
      <dt className="font-mono text-xs text-[var(--muted)]">{label}</dt>
      <dd className="break-words text-[var(--foreground)]">{value}</dd>
    </div>
  );
}

export function StatePanel({
  runId,
  status,
  state,
  interrupt,
  summary,
}: StatePanelProps) {
  return (
    <section>
      <h2 className="mb-3 font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
        Run state
      </h2>
      <div className="rounded-lg border border-[var(--border)] bg-[var(--panel)]/70 p-4">
        {!state && !runId ? (
          <p className="text-sm text-[var(--muted)]">No active run yet.</p>
        ) : (
          <dl>
            <Row label="run_id" value={runId ? <span className="font-mono text-xs">{runId}</span> : null} />
            <Row label="status" value={status} />
            <Row label="sku" value={state?.sku} />
            <Row label="qty" value={state?.quantity} />
            <Row label="best" value={
              state?.best_vendor
                ? `${state.best_vendor} @ $${state.best_price}`
                : null
            } />
            <Row label="history" value={
              state?.historical_price != null
                ? `$${state.historical_price}`
                : null
            } />
            <Row label="negotiate" value={
              state?.negotiate_vendor
                ? `${state.negotiate_vendor} @ $${state.negotiate_price}`
                : null
            } />
            <Row label="replan" value={
              state?.suggested_sku
                ? `${state.original_sku} → ${state.suggested_sku}`
                : null
            } />
            <Row label="HITL" value={state?.hitl_status} />
            <Row label="offers" value={
              state?.vendors?.length
                ? `${state.vendors.length} ranked`
                : null
            } />
            {interrupt ? (
              <Row
                label="interrupt"
                value={
                  <span className="text-amber-200">
                    {interrupt.type || "paused"} — approval UI in next step
                  </span>
                }
              />
            ) : null}
            {state?.email_draft ? (
              <div className="mt-3 border-t border-[var(--border)] pt-3">
                <p className="mb-1 font-mono text-xs text-[var(--muted)]">
                  draft preview
                </p>
                <p className="text-sm font-medium">
                  {state.email_draft.subject}
                </p>
                <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-[var(--muted)]">
                  {state.email_draft.body}
                </pre>
              </div>
            ) : null}
            {summary ? (
              <div className="mt-3 border-t border-[var(--border)] pt-3">
                <p className="mb-1 font-mono text-xs text-[var(--muted)]">
                  summary
                </p>
                <p className="text-sm leading-relaxed text-[var(--foreground)]/85">
                  {summary}
                </p>
              </div>
            ) : null}
          </dl>
        )}
      </div>
    </section>
  );
}
