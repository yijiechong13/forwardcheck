/**
 * Small shared presentation primitives.
 *
 * Deliberately not a component library — just the four shapes that repeat
 * across the result views, so spacing and border treatment stay consistent.
 */
import type { ReactNode } from "react";
import type { SourceTier, Verdict } from "@/lib/types";
import { TIER_LABEL, TIER_PIPS, VERDICT_STYLE } from "@/lib/verdict";

export function Section({
  index,
  title,
  description,
  action,
  children,
}: {
  index: string;
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="animate-fade-up">
      <div className="mb-4 flex items-end justify-between gap-4 border-b border-edge pb-3">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-[10px] tracking-[0.18em] text-fg-subtle">
              {index}
            </span>
            <h2 className="text-sm font-semibold tracking-tight text-fg">{title}</h2>
          </div>
          {description ? (
            <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-fg-muted">
              {description}
            </p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function VerdictBadge({
  verdict,
  size = "sm",
}: {
  verdict: Verdict;
  size?: "sm" | "lg";
}) {
  const style = VERDICT_STYLE[verdict];
  return (
    <span
      className={
        size === "lg"
          ? "inline-flex items-center rounded-md px-3 py-1.5 text-sm font-semibold tracking-tight"
          : "inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-[11px] font-semibold"
      }
      style={{ color: style.fg, background: style.bg }}
    >
      {style.label}
    </span>
  );
}

/** Authority shown as filled pips — rank without introducing colour. */
export function TierPips({ tier }: { tier: SourceTier }) {
  const filled = TIER_PIPS[tier];
  return (
    <span className="inline-flex items-center gap-2" title={`${TIER_LABEL[tier]} source`}>
      <span className="flex gap-[3px]" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="h-[3px] w-2.5 rounded-full"
            style={{
              background: i <= filled ? "var(--fg)" : "var(--border-strong)",
              opacity: i <= filled ? 0.85 : 0.5,
            }}
          />
        ))}
      </span>
      <span className="text-[11px] font-medium text-fg-muted">{TIER_LABEL[tier]}</span>
    </span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="h-1 w-12 overflow-hidden rounded-full"
        style={{ background: "var(--border)" }}
        role="img"
        aria-label={`Confidence ${Math.round(value * 100)} percent`}
      >
        <span
          className="block h-full rounded-full transition-[width] duration-500"
          style={{ width: `${Math.max(4, value * 100)}%`, background: "var(--fg)" }}
        />
      </span>
      <span className="tnum text-[11px] text-fg-muted">
        {Math.round(value * 100)}%
      </span>
    </span>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded border border-edge bg-bg-sunken px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-fg-muted">
      {children}
    </span>
  );
}
