"use client";

import { useEffect, useState } from "react";

type Health = {
  status: string;
  service: string;
  llm_provider: string;
  llm_model: string;
  finops_mode: string;
};

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
      <header className="space-y-3">
        <p className="font-mono text-sm tracking-wide text-[var(--muted)]">
          portfolio · agent layer
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          AI-Procurement-Agent
        </h1>
        <p className="max-w-xl text-base leading-relaxed text-[var(--muted)]">
          LangGraph ReAct workflow: search vendors, check FinOps history, draft
          negotiation email — pause for human approval. Workspace UI lands in
          Phase E.
        </p>
      </header>

      <section
        className="rounded-lg border border-[var(--border)] bg-[var(--panel)]/80 p-5"
        aria-live="polite"
      >
        <h2 className="mb-3 font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
          API health
        </h2>
        {error && (
          <p className="text-sm text-red-300">
            Backend unreachable ({error}). Start API on :8100.
          </p>
        )}
        {!error && !health && (
          <p className="text-sm text-[var(--muted)]">Checking…</p>
        )}
        {health && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 font-mono text-sm">
            <dt className="text-[var(--muted)]">status</dt>
            <dd>{health.status}</dd>
            <dt className="text-[var(--muted)]">service</dt>
            <dd>{health.service}</dd>
            <dt className="text-[var(--muted)]">llm</dt>
            <dd>
              {health.llm_provider} / {health.llm_model}
            </dd>
            <dt className="text-[var(--muted)]">finops</dt>
            <dd>{health.finops_mode}</dd>
          </dl>
        )}
      </section>
    </main>
  );
}
