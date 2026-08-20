import type { Claim, Evidence } from "@/lib/types";
import { formatDate, humaniseStatus } from "@/lib/verdict";
import { Pill, TierPips } from "./ui";

export function EvidenceCards({
  evidence,
  claims,
}: {
  evidence: Evidence[];
  claims: Claim[];
}) {
  const claimText = new Map(claims.map((c) => [c.id, c.text]));

  if (evidence.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-edge-strong bg-bg-raised px-5 py-8 text-center">
        <p className="text-[13px] text-fg-muted">
          No evidence passed the retrieval threshold for this message.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {evidence.map((doc) => (
        <article
          key={doc.id}
          className="flex flex-col rounded-lg border border-edge bg-bg-raised transition hover:border-edge-strong"
        >
          <div className="flex items-center justify-between gap-3 border-b border-edge px-4 py-2.5">
            <TierPips tier={doc.tier} />
            <div className="flex items-center gap-1.5">
              {doc.isMock ? <Pill>SAMPLE</Pill> : null}
              {!doc.isMock && !doc.fromFullPage ? <Pill>SNIPPET ONLY</Pill> : null}
              <Pill>{doc.id}</Pill>
            </div>
          </div>

          <div className="flex-1 px-4 py-3.5">
            <h3 className="text-[13px] font-semibold leading-snug text-fg">{doc.title}</h3>
            <p className="mt-1 text-[11px] text-fg-muted">
              {doc.publisher} · {doc.jurisdiction} ·{" "}
              {doc.publishedAt ? formatDate(doc.publishedAt) : "date not stated"}
            </p>

            {!doc.isMock && !doc.fromFullPage ? (
              <p className="mt-2 border-l-2 border-dashed border-edge-strong pl-2 text-[11px] leading-snug text-fg-muted">
                The page could not be fetched, so only the search snippet was
                available. Treated as weaker evidence.
              </p>
            ) : null}

            <blockquote className="mt-3 border-l-2 border-edge-strong pl-3 text-[12px] leading-relaxed text-fg-muted">
              {doc.snippet}
            </blockquote>

            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wide text-fg-subtle">
                Asserts
              </span>
              <Pill>{humaniseStatus(doc.statusAsserted)}</Pill>
            </div>
          </div>

          {/* Linking evidence back to specific claims is what makes this a
              citation rather than a vibe. */}
          {(doc.supportsClaimIds.length > 0 || doc.refutesClaimIds.length > 0) && (
            <div className="space-y-1.5 border-t border-edge px-4 py-3">
              {doc.supportsClaimIds.map((id) => (
                <p key={id} className="flex gap-2 text-[11px] leading-snug">
                  <span className="shrink-0 font-mono text-fg-subtle">SUPPORTS</span>
                  <span className="text-fg-muted">{claimText.get(id) ?? id}</span>
                </p>
              ))}
              {doc.refutesClaimIds.map((id) => (
                <p key={id} className="flex gap-2 text-[11px] leading-snug">
                  <span className="shrink-0 font-mono text-fg-subtle">REFUTES</span>
                  <span className="text-fg-muted">{claimText.get(id) ?? id}</span>
                </p>
              ))}
            </div>
          )}

          <div className="border-t border-edge px-4 py-2">
            {doc.isMock ? (
              // Seeded evidence uses placeholder URLs — never render them as
              // links, so a sample citation can never be mistaken for a real one.
              <span className="break-all font-mono text-[10px] text-fg-subtle">
                {doc.url}
              </span>
            ) : (
              <a
                href={doc.url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="break-all font-mono text-[10px] text-fg-muted underline decoration-dotted underline-offset-2 transition hover:text-fg"
              >
                {doc.url}
              </a>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
