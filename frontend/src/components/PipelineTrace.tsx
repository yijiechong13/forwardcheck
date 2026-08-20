"use client";

import { useState } from "react";
import type { PipelineStep } from "@/lib/types";

/**
 * Developer / evaluation panel.
 *
 * Exposes what each node did, which evidence IDs it touched, and why the
 * verdict came out the way it did. Collapsed by default so it does not
 * compete with the user-facing result.
 */
export function PipelineTrace({ trace }: { trace: PipelineStep[] }) {
  const [open, setOpen] = useState(false);
  const [openStep, setOpenStep] = useState<number | null>(null);
  const totalMs = trace.reduce((sum, step) => sum + step.durationMs, 0);

  return (
    <div className="rounded-lg border border-edge bg-bg-raised">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-bg-sunken"
      >
        <span className="flex items-center gap-2.5">
          <span
            className="font-mono text-[10px] text-fg-subtle transition-transform"
            style={{ transform: open ? "rotate(90deg)" : "none" }}
            aria-hidden
          >
            ▸
          </span>
          <span className="text-[13px] font-semibold text-fg">Pipeline trace</span>
          <span className="font-mono text-[10px] text-fg-subtle">
            {trace.length} NODES · {totalMs}MS
          </span>
        </span>
        <span className="text-[11px] text-fg-muted">{open ? "Hide" : "Show"}</span>
      </button>

      {open ? (
        <div className="border-t border-edge px-4 py-4">
          <ol className="space-y-2">
            {trace.map((step) => {
              const isOpen = openStep === step.step;
              return (
                <li key={step.step} className="rounded-md border border-edge bg-bg">
                  <button
                    type="button"
                    onClick={() => setOpenStep(isOpen ? null : step.step)}
                    aria-expanded={isOpen}
                    className="flex w-full items-start gap-3 px-3 py-2.5 text-left transition hover:bg-bg-sunken"
                  >
                    <span className="tnum mt-px font-mono text-[10px] text-fg-subtle">
                      {String(step.step).padStart(2, "0")}
                    </span>
                    <span className="flex-1">
                      <span className="block font-mono text-[12px] font-medium text-fg">
                        {step.node}
                      </span>
                      <span className="mt-0.5 block text-[11px] leading-snug text-fg-muted">
                        {step.summary}
                      </span>
                    </span>
                    <span className="tnum shrink-0 font-mono text-[10px] text-fg-subtle">
                      {step.durationMs}ms
                    </span>
                  </button>

                  {isOpen ? (
                    <pre className="overflow-x-auto border-t border-edge px-3 py-2.5 font-mono text-[11px] leading-relaxed text-fg-muted">
                      {JSON.stringify(step.details, null, 2)}
                    </pre>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}
    </div>
  );
}
