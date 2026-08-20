"use client";

import { useEffect, useState } from "react";
import { EXAMPLE_CLAIMS } from "@/lib/examples";

const MAX_CHARS = 4000;

/**
 * Staged progress labels. The live pipeline runs decomposition, then
 * retrieval, then grading, and each takes seconds — a single spinner makes a
 * working request look hung. These advance on a timer rather than from server
 * events: honest about ordering, and it costs nothing extra.
 */
const STAGES = [
  "Extracting claims",
  "Searching sources",
  "Reading pages",
  "Grading evidence",
];

export function InputPanel({
  onVerify,
  isLoading,
  error,
  isLive = false,
}: {
  onVerify: (message: string) => void;
  isLoading: boolean;
  error?: string | null;
  isLive?: boolean;
}) {
  const [message, setMessage] = useState("");
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!isLoading) return;
    // Hold on the final stage rather than looping, so a slow request does not
    // appear to restart. The counter is reset on cleanup rather than in the
    // effect body, which avoids a synchronous setState during render.
    const timer = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      isLive ? 2600 : 400,
    );
    return () => {
      clearInterval(timer);
      setStage(0);
    };
  }, [isLoading, isLive]);
  const trimmed = message.trim();
  const canSubmit = trimmed.length >= 12 && !isLoading;

  return (
    <div className="rounded-lg border border-edge bg-bg-raised">
      <div className="flex items-center justify-between border-b border-edge px-4 py-2.5">
        <span className="font-mono text-[10px] tracking-[0.18em] text-fg-subtle">
          FORWARDED MESSAGE
        </span>
        <span className="tnum text-[11px] text-fg-subtle">
          {trimmed.length}/{MAX_CHARS}
        </span>
      </div>

      <div className="p-4">
        <label htmlFor="fc-message" className="sr-only">
          Paste the forwarded message you want to verify
        </label>
        <textarea
          id="fc-message"
          value={message}
          onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && canSubmit) {
              onVerify(trimmed);
            }
          }}
          rows={7}
          disabled={isLoading}
          placeholder={"Paste the message exactly as you received it \u2014 including the emoji and the \u201cforward to everyone\u201d line. Formatting is a signal too."}
          className="w-full resize-y rounded-md border border-edge bg-bg px-3.5 py-3 text-[14px] leading-relaxed text-fg outline-none transition placeholder:text-fg-subtle focus:border-edge-strong focus:ring-1 focus:ring-[var(--border-strong)] disabled:opacity-60"
        />

        <div className="mt-4">
          <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-fg-subtle">
            OR TRY A SEEDED EXAMPLE
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {EXAMPLE_CLAIMS.map((example) => (
              <button
                key={example.id}
                type="button"
                disabled={isLoading}
                onClick={() => setMessage(example.message)}
                className="group rounded-md border border-edge bg-bg px-3 py-2.5 text-left transition hover:border-edge-strong hover:bg-bg-sunken disabled:opacity-50"
              >
                <span className="block text-[12px] font-semibold text-fg">
                  {example.label}
                </span>
                <span className="mt-0.5 block text-[11px] leading-snug text-fg-muted">
                  {example.blurb}
                </span>
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <p
            role="alert"
            className="mt-4 rounded-md border px-3 py-2 text-[12px]"
            style={{
              color: "var(--verdict-false)",
              background: "var(--verdict-false-bg)",
              borderColor: "var(--verdict-false)",
            }}
          >
            {error}
          </p>
        ) : null}

        <div className="mt-4 flex items-center justify-between gap-4 border-t border-edge pt-4">
          <p className="text-[11px] leading-snug text-fg-subtle">
            {isLive
              ? "Searches live sources and grades each claim. Runs only when you submit."
              : "Runs a 7-step evidence pipeline over seeded sample evidence. Nothing is stored."}
          </p>
          <button
            type="button"
            onClick={() => canSubmit && onVerify(trimmed)}
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-[13px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: "var(--fg)", color: "var(--bg)" }}
          >
            {isLoading ? (
              <>
                <span
                  className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
                  aria-hidden
                />
                {STAGES[stage]}
              </>
            ) : (
              <>
                Verify claim
                <kbd className="font-mono text-[10px] opacity-60">⌘↵</kbd>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
