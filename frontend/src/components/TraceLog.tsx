"use client";

import type { TraceEvent } from "@/lib/api";

type TraceLogProps = {
  events: TraceEvent[];
  busy: boolean;
};

function kindClass(kind?: string) {
  switch (kind) {
    case "thought":
      return "text-sky-300";
    case "action":
      return "text-amber-300";
    case "observation":
      return "text-emerald-300";
    case "status":
      return "text-violet-300";
    default:
      return "text-[var(--muted)]";
  }
}

export function TraceLog({ events, busy }: TraceLogProps) {
  return (
    <section className="flex min-h-[280px] flex-col">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
          Thought / Action / Observation
        </h2>
        <span className="font-mono text-xs text-[var(--muted)]">
          {events.length} step{events.length === 1 ? "" : "s"}
          {busy ? " · live" : ""}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--panel)]/70 p-3">
        {events.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            Run a goal to stream agent steps here.
          </p>
        ) : (
          events.map((ev, idx) => (
            <article
              key={`${ev.node}-${idx}-${ev.message?.slice(0, 24)}`}
              className="border-b border-[var(--border)]/60 pb-2 last:border-0"
            >
              <div className="mb-1 flex flex-wrap items-center gap-2 font-mono text-[11px]">
                <span className={kindClass(ev.kind)}>{ev.kind || "event"}</span>
                <span className="text-[var(--muted)]">·</span>
                <span className="text-[var(--foreground)]">{ev.node}</span>
              </div>
              <p className="text-sm leading-relaxed text-[var(--foreground)]/90">
                {ev.message}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
