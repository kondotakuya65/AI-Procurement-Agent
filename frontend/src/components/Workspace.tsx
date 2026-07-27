"use client";

import { useEffect, useState } from "react";
import { GoalPanel } from "@/components/GoalPanel";
import { Header } from "@/components/Header";
import { StatePanel } from "@/components/StatePanel";
import { TraceLog } from "@/components/TraceLog";
import {
  DEMO_GOAL,
  fetchHealth,
  streamCreateRun,
  type RunInterrupt,
  type RunState,
  type TraceEvent,
} from "@/lib/api";

export function Workspace() {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [llmProvider, setLlmProvider] = useState<string>();
  const [finopsMode, setFinopsMode] = useState<string>();
  const [goal, setGoal] = useState(DEMO_GOAL);
  const [busy, setBusy] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [state, setState] = useState<RunState | null>(null);
  const [interrupt, setInterrupt] = useState<RunInterrupt | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ text: string; kind: "ok" | "error" } | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const health = await fetchHealth();
        if (cancelled) return;
        setHealthy(health.status === "ok");
        setLlmProvider(health.llm_provider);
        setFinopsMode(health.finops_mode);
      } catch {
        if (!cancelled) {
          setHealthy(false);
          setBanner({
            text: "Backend offline — start FastAPI on :8100",
            kind: "error",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit() {
    setBusy(true);
    setBanner(null);
    setTraces([]);
    setState(null);
    setInterrupt(null);
    setSummary(null);
    setRunId(null);
    setStatus("running");

    try {
      for await (const event of streamCreateRun(goal.trim())) {
        if (event.type === "status" && event.run_id) {
          setRunId(event.run_id);
          setStatus(event.status || "running");
        }
        if (event.type === "trace") {
          setTraces((prev) => [
            ...prev,
            {
              kind: event.kind,
              node: event.node,
              message: event.message,
              data: event.data,
            },
          ]);
        }
        if (event.type === "interrupt") {
          setInterrupt(event.interrupt || null);
          setStatus("awaiting_hitl");
        }
        if (event.type === "error") {
          setBanner({ text: event.error || "Run failed", kind: "error" });
          setStatus("failed");
        }
        if (event.type === "done") {
          setRunId(event.run_id || null);
          setStatus(event.status || null);
          setState(event.state || null);
          setInterrupt(event.interrupt || null);
          setSummary(event.summary || event.state?.summary || null);
          if (event.state?.trace?.length) {
            setTraces(event.state.trace);
          }
          if (event.status === "awaiting_hitl") {
            setBanner({
              text: "Agent paused for human approval — HITL panel lands in E2.",
              kind: "ok",
            });
          } else if (event.status === "completed") {
            setBanner({ text: "Run completed.", kind: "ok" });
          }
        }
      }
    } catch (err) {
      setBanner({
        text: err instanceof Error ? err.message : "Stream failed",
        kind: "error",
      });
      setStatus("failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Header
        healthy={healthy}
        llmProvider={llmProvider}
        finopsMode={finopsMode}
        statusLabel={status || undefined}
      />
      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="space-y-6">
          {banner ? (
            <p
              className={`rounded-lg px-3 py-2 text-sm ${
                banner.kind === "error"
                  ? "border border-rose-900/50 bg-rose-950/40 text-rose-200"
                  : "border border-emerald-900/40 bg-emerald-950/30 text-emerald-200"
              }`}
            >
              {banner.text}
            </p>
          ) : null}
          <GoalPanel
            goal={goal}
            busy={busy}
            onGoalChange={setGoal}
            onSubmit={onSubmit}
            onUseDemo={() => setGoal(DEMO_GOAL)}
          />
          <TraceLog events={traces} busy={busy} />
        </div>
        <StatePanel
          runId={runId}
          status={status}
          state={state}
          interrupt={interrupt}
          summary={summary}
        />
      </main>
    </div>
  );
}
