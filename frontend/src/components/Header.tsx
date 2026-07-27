"use client";

type HeaderProps = {
  healthy: boolean | null;
  llmProvider?: string;
  finopsMode?: string;
  statusLabel?: string;
};

export function Header({
  healthy,
  llmProvider,
  finopsMode,
  statusLabel,
}: HeaderProps) {
  const healthText =
    healthy === null ? "checking" : healthy ? "online" : "offline";
  const healthColor =
    healthy === null
      ? "text-[var(--muted)]"
      : healthy
        ? "text-emerald-300"
        : "text-rose-300";

  return (
    <header className="border-b border-[var(--border)]/80 bg-[var(--panel)]/40 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-4 px-4 py-5 sm:px-6">
        <div>
          <p className="font-mono text-xs tracking-wide text-[var(--muted)]">
            portfolio · agent layer
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            AI-Procurement-Agent
          </h1>
        </div>
        <dl className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-xs text-[var(--muted)]">
          <div>
            api{" "}
            <span className={healthColor}>{healthText}</span>
          </div>
          {llmProvider ? (
            <div>
              llm <span className="text-[var(--foreground)]">{llmProvider}</span>
            </div>
          ) : null}
          {finopsMode ? (
            <div>
              finops{" "}
              <span className="text-[var(--foreground)]">{finopsMode}</span>
            </div>
          ) : null}
          {statusLabel ? (
            <div>
              run <span className="text-[var(--accent)]">{statusLabel}</span>
            </div>
          ) : null}
        </dl>
      </div>
    </header>
  );
}
