"use client";

type GoalPanelProps = {
  goal: string;
  busy: boolean;
  onGoalChange: (value: string) => void;
  onSubmit: () => void;
  onUseDemo: () => void;
};

export function GoalPanel({
  goal,
  busy,
  onGoalChange,
  onSubmit,
  onUseDemo,
}: GoalPanelProps) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
          Goal
        </h2>
        <button
          type="button"
          className="font-mono text-xs text-[var(--accent)] hover:underline"
          onClick={onUseDemo}
          disabled={busy}
        >
          use demo goal
        </button>
      </div>
      <textarea
        value={goal}
        onChange={(e) => onGoalChange(e.target.value)}
        rows={4}
        disabled={busy}
        placeholder="Describe what to procure…"
        className="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 py-3 text-sm leading-relaxed text-[var(--foreground)] outline-none ring-[var(--accent)] placeholder:text-[var(--muted)] focus:ring-1 disabled:opacity-60"
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={busy || goal.trim().length < 3}
        className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Running…" : "Run agent"}
      </button>
    </section>
  );
}
