"use client";

import { Fragment, useState } from "react";
import type { Claim } from "@/lib/types";
import {
  DOMAIN_LABEL,
  GRADE_LABEL,
  humaniseStatus,
} from "@/lib/verdict";
import { ConfidenceBar, Pill, VerdictBadge } from "./ui";

export function ClaimsTable({ claims }: { claims: Claim[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="overflow-hidden rounded-lg border border-edge bg-bg-raised">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="border-b border-edge bg-bg-sunken">
              {["Extracted claim", "Status type", "Verdict", "Confidence", "Key reason"].map(
                (heading) => (
                  <th
                    key={heading}
                    scope="col"
                    className="px-4 py-2.5 font-mono text-[10px] font-medium tracking-[0.16em] text-fg-subtle"
                  >
                    {heading.toUpperCase()}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => {
              const isOpen = expanded === claim.id;
              return (
                <Fragment key={claim.id}>
                  <tr
                    onClick={() => setExpanded(isOpen ? null : claim.id)}
                    className="cursor-pointer border-b border-edge align-top transition last:border-0 hover:bg-bg-sunken"
                  >
                    <td className="px-4 py-3.5">
                      <div className="flex items-start gap-2">
                        <span
                          className="mt-1 font-mono text-[10px] text-fg-subtle transition-transform"
                          style={{ transform: isOpen ? "rotate(90deg)" : "none" }}
                          aria-hidden
                        >
                          ▸
                        </span>
                        <div>
                          <span className="text-[13px] font-medium leading-snug text-fg">
                            {claim.text}
                          </span>
                          {claim.isEscalation ? (
                            <span className="mt-1.5 flex items-center gap-1.5 font-mono text-[10px] text-fg-muted">
                              <span className="rounded-sm border border-edge px-1 py-px">
                                ESCALATION
                              </span>
                              {claim.escalationFrom} → {claim.escalationTo}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="block text-[12px] font-medium text-fg">
                        {humaniseStatus(claim.statusType)}
                      </span>
                      <span className="text-[11px] text-fg-muted">
                        {DOMAIN_LABEL[claim.domain]} · {claim.jurisdiction}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <VerdictBadge verdict={claim.verdict} />
                    </td>
                    <td className="px-4 py-3.5">
                      <ConfidenceBar value={claim.confidence} />
                    </td>
                    <td className="max-w-sm px-4 py-3.5 text-[12px] leading-relaxed text-fg-muted">
                      {claim.keyReason}
                    </td>
                  </tr>

                  {isOpen ? (
                    <tr className="border-b border-edge bg-bg-sunken">
                      <td colSpan={5} className="px-4 py-4">
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <div className="mb-1.5 font-mono text-[10px] tracking-[0.16em] text-fg-subtle">
                              ORIGINAL WORDING
                            </div>
                            <p className="border-l-2 border-edge-strong pl-3 text-[12px] italic leading-relaxed text-fg-muted">
                              &ldquo;{claim.sourceSpan}&rdquo;
                            </p>
                          </div>
                          <div>
                            <div className="mb-1.5 font-mono text-[10px] tracking-[0.16em] text-fg-subtle">
                              EVIDENCE GRADING
                            </div>
                            {claim.grades.length === 0 ? (
                              <p className="text-[12px] text-fg-muted">
                                No evidence passed the retrieval threshold.
                              </p>
                            ) : (
                              <ul className="space-y-1.5">
                                {claim.grades.map((grade) => (
                                  <li
                                    key={grade.evidenceId}
                                    className="flex items-start gap-2 text-[12px] leading-relaxed"
                                  >
                                    <Pill>{grade.evidenceId}</Pill>
                                    <span className="text-fg-muted">
                                      <strong className="font-semibold text-fg">
                                        {GRADE_LABEL[grade.label]}
                                      </strong>{" "}
                                      — {grade.rationale}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
