"use client";

import { useEffect, useState } from "react";
import type { EmailDraft } from "@/lib/api";

type HitlPanelProps = {
  open: boolean;
  busy: boolean;
  draft: EmailDraft | null;
  vendor?: string | null;
  prompt?: string | null;
  onApprove: () => void;
  onReject: () => void;
  onEdit: (editedDraft: string) => void;
};

function draftToEditableText(draft: EmailDraft | null): string {
  if (!draft) return "";
  const subject = draft.subject || "";
  const body = draft.body || "";
  return `Subject: ${subject}\n\n${body}`.trim();
}

export function HitlPanel({
  open,
  busy,
  draft,
  vendor,
  prompt,
  onApprove,
  onReject,
  onEdit,
}: HitlPanelProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");

  useEffect(() => {
    if (open) {
      setEditing(false);
      setEditText(draftToEditableText(draft));
    }
  }, [open, draft]);

  if (!open || !draft) return null;

  return (
    <section className="rounded-lg border border-amber-500/35 bg-amber-950/20 p-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-mono text-xs uppercase tracking-wider text-amber-200/90">
          Human approval required
        </h2>
        {vendor ? (
          <span className="font-mono text-xs text-[var(--muted)]">to {vendor}</span>
        ) : null}
      </div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        {prompt ||
          "Review the negotiation email. Approve to write outbox, edit then save, or reject."}
      </p>

      {!editing ? (
        <div className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--panel)]/80 p-3">
          <p className="text-sm font-medium text-[var(--foreground)]">
            {draft.subject}
          </p>
          <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-[var(--muted)]">
            {draft.body}
          </pre>
        </div>
      ) : (
        <textarea
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          rows={12}
          disabled={busy}
          className="mb-4 w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 py-3 font-mono text-xs leading-relaxed text-[var(--foreground)] outline-none ring-amber-400/50 focus:ring-1 disabled:opacity-60"
        />
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onApprove}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:brightness-110 disabled:opacity-50"
        >
          Approve
        </button>
        {!editing ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setEditText(draftToEditableText(draft));
              setEditing(true);
            }}
            className="rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm text-[var(--foreground)] hover:border-[var(--accent)] disabled:opacity-50"
          >
            Edit
          </button>
        ) : (
          <button
            type="button"
            disabled={busy || editText.trim().length < 3}
            onClick={() => onEdit(editText)}
            className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:brightness-110 disabled:opacity-50"
          >
            Save edit &amp; send to outbox
          </button>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={onReject}
          className="rounded-lg border border-rose-800/60 bg-rose-950/40 px-3 py-2 text-sm text-rose-100 hover:bg-rose-950/70 disabled:opacity-50"
        >
          Reject
        </button>
        {editing ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => setEditing(false)}
            className="rounded-lg px-3 py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-50"
          >
            Cancel edit
          </button>
        ) : null}
      </div>
    </section>
  );
}
