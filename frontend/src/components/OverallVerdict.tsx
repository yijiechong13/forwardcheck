import type { VerifyResponse } from "@/lib/types";
import { confidenceLabel, formatTimestamp, VERDICT_STYLE } from "@/lib/verdict";
import { VerdictBadge } from "./ui";

export function OverallVerdict({ result }: { result: VerifyResponse }) {
  const style = VERDICT_STYLE[result.overallVerdict];
  const counts = result.claims.reduce<Record<string, number>>((acc, claim) => {
    acc[claim.verdict] = (acc[claim.verdict] ?? 0) + 1;
    return acc;
  }, {});
  const escalations = result.claims.filter((c) => c.isEscalation).length;

  return (
    <div
      className="animate-fade-up overflow-hidden rounded-lg border"
      style={{ borderColor: style.fg, background: "var(--bg-raised)" }}
    >
      {/* Verdict header sits on the accent so the label reads first. */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
        style={{ background: style.bg }}
      >
        <div className="flex items-center gap-3">
          <VerdictBadge verdict={result.overallVerdict} size="lg" />
          <span className="text-[12px]" style={{ color: style.fg }}>
            {style.gloss}
          </span>
        </div>
        <div className="text-right">
          <div className="font-mono text-[10px] tracking-[0.16em] text-fg-subtle">
            CONFIDENCE
          </div>
          <div className="tnum text-[13px] font-semibold" style={{ color: style.fg }}>
            {confidenceLabel(result.confidence)} · {Math.round(result.confidence * 100)}%
          </div>
        </div>
      </div>

      <div className="px-5 py-4">
        <p className="max-w-3xl text-[14px] leading-relaxed text-fg">{result.summary}</p>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-edge pt-3.5 text-[11px] text-fg-muted">
          <span className="tnum">
            <strong className="font-semibold text-fg">{result.claims.length}</strong> claims
            extracted
          </span>
          {Object.entries(counts).map(([verdict, count]) => (
            <span key={verdict} className="tnum">
              <strong className="font-semibold text-fg">{count}</strong> {verdict.toLowerCase()}
            </span>
          ))}
          {escalations > 0 ? (
            <span className="tnum">
              <strong className="font-semibold text-fg">{escalations}</strong> status
              escalation{escalations === 1 ? "" : "s"} detected
            </span>
          ) : null}
          <span className="ml-auto font-mono text-[10px] tracking-wide text-fg-subtle">
            LAST CHECKED {formatTimestamp(result.lastChecked)}
          </span>
        </div>
      </div>
    </div>
  );
}
