/**
 * Presentation helpers for the closed verdict vocabulary.
 *
 * Kept in one place so a verdict looks identical everywhere it appears —
 * overall card, claims table, and share card cannot drift apart.
 */
import type { Domain, GradeLabel, SourceTier, Verdict } from "./types";

export const VERDICT_STYLE: Record<
  Verdict,
  { fg: string; bg: string; label: string; gloss: string }
> = {
  Supported: {
    fg: "var(--verdict-supported)",
    bg: "var(--verdict-supported-bg)",
    label: "Supported",
    gloss: "Evidence backs this claim as stated.",
  },
  Misleading: {
    fg: "var(--verdict-misleading)",
    bg: "var(--verdict-misleading-bg)",
    label: "Misleading",
    gloss: "Partly true, but the status or scope is overstated.",
  },
  False: {
    fg: "var(--verdict-false)",
    bg: "var(--verdict-false-bg)",
    label: "False",
    gloss: "Evidence directly contradicts this claim.",
  },
  Outdated: {
    fg: "var(--verdict-outdated)",
    bg: "var(--verdict-outdated-bg)",
    label: "Outdated",
    gloss: "Was accurate once; the status has since moved on.",
  },
  "Insufficient evidence": {
    fg: "var(--verdict-insufficient)",
    bg: "var(--verdict-insufficient-bg)",
    label: "Insufficient evidence",
    gloss: "No retrieved source answers this claim either way.",
  },
};

export const TIER_LABEL: Record<SourceTier, string> = {
  primary: "Primary",
  official: "Official",
  credible_news: "Credible news",
  secondary: "Secondary",
};

/** Filled pips communicate authority at a glance without adding colour. */
export const TIER_PIPS: Record<SourceTier, number> = {
  primary: 4,
  official: 3,
  credible_news: 2,
  secondary: 1,
};

export const GRADE_LABEL: Record<GradeLabel, string> = {
  supports: "Supports",
  refutes: "Refutes",
  partially_supports: "Partially supports",
  does_not_answer: "Does not answer",
};

export const DOMAIN_LABEL: Record<Domain, string> = {
  legal: "Legal status",
  product_safety: "Product safety",
  policy: "Policy",
  unknown: "Unclassified",
};

/** Status keys are snake_case on the wire; render them as prose. */
export function humaniseStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.75) return "High";
  if (confidence >= 0.5) return "Moderate";
  return "Low";
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Singapore",
  }).format(d);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en-SG", { dateStyle: "medium" }).format(d);
}
