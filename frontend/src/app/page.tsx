"use client";

import { useState } from "react";
import { ClaimsTable } from "@/components/ClaimsTable";
import { EvidenceCards } from "@/components/EvidenceCards";
import { InputPanel } from "@/components/InputPanel";
import { OverallVerdict } from "@/components/OverallVerdict";
import { PipelineTrace } from "@/components/PipelineTrace";
import { ShareCorrection } from "@/components/ShareCorrection";
import { Timeline } from "@/components/Timeline";
import { Section } from "@/components/ui";
import { ApiError, verifyMessage } from "@/lib/api";
import type { VerifyResponse } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      <Header />

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
              description="The message broken into atomic, individually checkable statements. Select a row to see the original wording and how each source was graded."
            >
              <ClaimsTable claims={result.claims} />
            </Section>

            <Section
              index="03"
              title="Evidence"
              description="Sources retrieved for these claims, ranked by authority. Each card states which claim it supports or refutes."
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
              description="Where this event actually sits on the status ladder. Stages with no supporting evidence are marked rather than omitted."
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

function Header() {
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
            ForwardCheck
          </span>
        </div>

        <h1 className="mt-6 max-w-2xl text-3xl font-semibold leading-[1.15] tracking-tight text-fg sm:text-4xl">
          Verify forwarded news claims before you pass them on.
        </h1>
        <p className="mt-3.5 max-w-xl text-[14px] leading-relaxed text-fg-muted">
          Forwarded messages rarely invent an event. They take a real one and push its
          status one rung too far — investigated becomes charged, a maximum penalty
          becomes an automatic fine. ForwardCheck checks each claim separately, against
          cited evidence, for Singapore and Malaysia.
        </p>

        <div className="mt-6 flex flex-wrap gap-x-5 gap-y-1.5 font-mono text-[10px] tracking-[0.14em] text-fg-subtle">
          <span>LEGAL STATUS</span>
          <span>PRODUCT SAFETY</span>
          <span>POLICY &amp; REGULATION</span>
        </div>
      </div>
    </header>
  );
}

function EmptyState() {
  const steps = [
    ["Normalise", "Strip forwarding cruft, emoji, and urgency markers."],
    ["Decompose", "Split the message into atomic checkable claims."],
    ["Route", "Classify each claim by status type, domain, jurisdiction."],
    ["Retrieve", "Pull candidate evidence, ranked by source authority."],
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
          ForwardCheck · status verification for Singapore and Malaysia
        </p>
        <p className="font-mono text-[10px] tracking-wide text-fg-subtle">
          MOCK MODE · NO API KEYS REQUIRED
        </p>
      </div>
    </footer>
  );
}
