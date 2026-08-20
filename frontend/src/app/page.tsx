"use client";

import { useEffect, useState } from "react";
import { ClaimsTable } from "@/components/ClaimsTable";
import { EvidenceCards } from "@/components/EvidenceCards";
import { InputPanel } from "@/components/InputPanel";
import { OverallVerdict } from "@/components/OverallVerdict";
import { PipelineTrace } from "@/components/PipelineTrace";
import { ShareCorrection } from "@/components/ShareCorrection";
import { Timeline } from "@/components/Timeline";
import { Section } from "@/components/ui";
import { ApiError, checkHealth, verifyMessage } from "@/lib/api";
import type { VerifyResponse } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  // Surface backend availability on load. A reviewer who forgot to start
  // uvicorn should learn that from the page, not from a failed verification.
  useEffect(() => {
    void checkHealth().then(setApiUp);
  }, []);

  async function handleVerify(message: string) {
    setIsLoading(true);
    setError(null);
    try {
      setResult(await verifyMessage(message));
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong while verifying this message.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg">
      <Header apiUp={apiUp} />

      <main className="mx-auto max-w-5xl px-5 pb-24 sm:px-8">
        <div className="py-8">
          <InputPanel onVerify={handleVerify} isLoading={isLoading} error={error} />
        </div>

        {result ? (
          <div className="space-y-10">
            <Section
              index="01"
              title="Overall verdict"
              description="A single label for the message as a whole, derived from the claim-level verdicts below."
            >
              <OverallVerdict result={result} />
            </Section>

            <Section
              index="02"
              title="Extracted claims"
              description="The message broken into atomic, individually checkable claims. Select a row to see the original wording and how each source was graded."
            >
              <ClaimsTable claims={result.claims} />
            </Section>

            <Section
              index="03"
              title="Evidence"
              description="Sources retrieved for these claims, ranked by authority: official and primary Singapore sources above credible news. Each card states which claim it supports or refutes."
              action={
                <span className="hidden shrink-0 text-[11px] text-fg-subtle sm:block">
                  {result.evidence.length} documents
                </span>
              }
            >
              <EvidenceCards evidence={result.evidence} claims={result.claims} />
            </Section>

            <Section
              index="04"
              title="Status timeline"
              description="Where this matter actually sits on the status ladder — investigated, charged, convicted; proposed, passed, enforced; advisory, recall, ban. Stages with no supporting evidence are marked rather than omitted."
            >
              <Timeline timeline={result.timeline} />
            </Section>

            <Section
              index="05"
              title="Correction to share"
              description="A short reply you can send back to the group the message came from."
            >
              <ShareCorrection text={result.shareableCorrection} />
            </Section>

            <Section
              index="06"
              title="Developer trace"
              description="Every pipeline node, its inputs and outputs, and the rule that produced the final verdict."
            >
              <PipelineTrace trace={result.pipelineTrace} />
            </Section>

            <MockNotice notice={result.mockNotice} />
          </div>
        ) : (
          <EmptyState />
        )}
      </main>

      <Footer />
    </div>
  );
}

function Header({ apiUp }: { apiUp: boolean | null }) {
  return (
    <header className="relative overflow-hidden border-b border-edge">
      <div className="grid-bg pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative mx-auto max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="flex items-center gap-2.5">
          <span
            className="flex h-7 w-7 items-center justify-center rounded font-mono text-[13px] font-bold"
            style={{ background: "var(--fg)", color: "var(--bg)" }}
            aria-hidden
          >
            F
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-fg">
            ForwardCheck<span className="text-fg-subtle"> SG</span>
          </span>
        </div>

        <h1 className="mt-6 max-w-2xl text-3xl font-semibold leading-[1.15] tracking-tight text-fg sm:text-4xl">
          Verify forwarded claims before you pass them on.
        </h1>
        <p className="mt-3.5 max-w-2xl text-[14px] leading-relaxed text-fg-muted">
          Forwarded messages rarely invent an event. They take a real one and overstate
          it — a maximum fine becomes automatic, one recalled batch becomes every
          bottle, a payout per household becomes one per person. ForwardCheck SG
          decomposes each message into separate claims, retrieves official Singapore
          source evidence, and produces claim-level verdicts with citations, timelines
          and a correction you can send back.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-[10px] tracking-[0.14em] text-fg-subtle">
          <span>SINGAPORE</span>
          <span>POLICY &amp; REGULATION</span>
          <span>FINES &amp; ELIGIBILITY</span>
          <span>RECALLS</span>
          <span>LEGAL STATUS</span>
          {apiUp === false ? (
            <span
              className="rounded-sm border px-1.5 py-0.5 tracking-normal"
              style={{
                color: "var(--verdict-false)",
                borderColor: "var(--verdict-false)",
              }}
            >
              API OFFLINE — start the backend on :8000
            </span>
          ) : null}
        </div>
      </div>
    </header>
  );
}

function EmptyState() {
  const steps = [
    ["Normalise", "Strip forwarding cruft, emoji, and urgency markers."],
    ["Decompose", "Split into atomic claims — status, scope, and penalty."],
    ["Route", "Classify by status type, domain, and jurisdiction."],
    ["Retrieve", "Pull official Singapore evidence, ranked by authority."],
    ["Grade", "Judge each source: supports, refutes, partial, silent."],
    ["Verdict", "Assign per-claim verdicts, then an overall label."],
  ];

  return (
    <div className="animate-fade-up rounded-lg border border-dashed border-edge-strong px-6 py-10">
      <p className="text-center text-[13px] text-fg-muted">
        Paste a forwarded message above, or load one of the seeded examples.
      </p>
      <div className="mx-auto mt-8 grid max-w-3xl gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
        {steps.map(([name, description], index) => (
          <div key={name} className="border-t border-edge pt-2.5">
            <div className="flex items-baseline gap-2">
              <span className="tnum font-mono text-[10px] text-fg-subtle">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-[12px] font-semibold text-fg">{name}</span>
            </div>
            <p className="mt-1 text-[11px] leading-snug text-fg-muted">{description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockNotice({ notice }: { notice: string }) {
  return (
    <p className="rounded-md border border-dashed border-edge-strong bg-bg-sunken px-4 py-3 text-[11px] leading-relaxed text-fg-muted">
      <strong className="font-semibold text-fg">Sample data.</strong> {notice}
    </p>
  );
}

function Footer() {
  return (
    <footer className="border-t border-edge">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-5 py-6 sm:px-8">
        <p className="text-[11px] text-fg-subtle">
          ForwardCheck SG · public-status verification for forwarded claims
        </p>
        <p className="font-mono text-[10px] tracking-wide text-fg-subtle">
          MOCK MODE · NO API KEYS REQUIRED
        </p>
      </div>
    </footer>
  );
}
