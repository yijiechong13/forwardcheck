import type { TimelineEntry } from "@/lib/types";
import { formatDate } from "@/lib/verdict";
import { Pill } from "./ui";

/**
 * The status ladder, rendered in order.
 *
 * Missing rungs are drawn explicitly rather than omitted — the gap between
 * "charged" and "convicted" is usually the whole story in a forwarded claim.
 */
export function Timeline({ timeline }: { timeline: TimelineEntry[] }) {
  if (timeline.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-edge-strong bg-bg-raised px-5 py-8 text-center">
        <p className="text-[13px] text-fg-muted">
          No status timeline could be constructed for this message.
        </p>
      </div>
    );
  }

  return (
    <ol className="relative rounded-lg border border-edge bg-bg-raised px-5 py-5">
      {timeline.map((entry, index) => {
        const isLast = index === timeline.length - 1;
        return (
          <li key={`${entry.stage}-${index}`} className="relative flex gap-4 pb-5 last:pb-0">
            {/* Connector line, dashed through gaps in the evidence. */}
            {!isLast && (
              <span
                className="absolute left-[7px] top-4 h-full w-px"
                style={{
                  background: entry.found ? "var(--border-strong)" : "transparent",
                  backgroundImage: entry.found
                    ? undefined
                    : "linear-gradient(to bottom, var(--border) 50%, transparent 50%)",
                  backgroundSize: entry.found ? undefined : "1px 6px",
                }}
                aria-hidden
              />
            )}

            <span
              className="relative z-10 mt-1 h-[15px] w-[15px] shrink-0 rounded-full border-2"
              style={{
                background: entry.found ? "var(--fg)" : "var(--bg-raised)",
                borderColor: entry.found ? "var(--fg)" : "var(--border-strong)",
                borderStyle: entry.found ? "solid" : "dashed",
              }}
              aria-hidden
            />

            <div className={entry.found ? "" : "opacity-70"}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[13px] font-semibold text-fg">{entry.label}</span>
                <span className="tnum font-mono text-[11px] text-fg-muted">
                  {formatDate(entry.date)}
                </span>
                {!entry.found ? (
                  <span className="rounded-sm border border-dashed border-edge-strong px-1.5 py-px font-mono text-[9px] tracking-wide text-fg-subtle">
                    NOT FOUND IN AVAILABLE EVIDENCE
                  </span>
                ) : null}
              </div>
              <p className="mt-1 max-w-2xl text-[12px] leading-relaxed text-fg-muted">
                {entry.description}
              </p>
              {entry.evidenceIds.length > 0 ? (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {entry.evidenceIds.map((id) => (
                    <Pill key={id}>{id}</Pill>
                  ))}
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
