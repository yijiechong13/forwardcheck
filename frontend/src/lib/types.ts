/**
 * Shared types for the ForwardCheck verification contract.
 *
 * These mirror the FastAPI Pydantic models in `backend/app/models/schemas.py`.
 * The backend serialises with camelCase aliases so this file is the single
 * source of truth on the client and no mapping layer is needed.
 */

/** The closed set of verdict labels. Free-text verdicts cannot be evaluated. */
export type Verdict =
  | "Supported"
  | "Misleading"
  | "False"
  | "Outdated"
  | "Insufficient evidence";

/** How authoritative a source is. Drives ranking and UI weight. */
export type SourceTier = "primary" | "official" | "credible_news" | "secondary";

/**
 * Singapore-only MVP. "Overseas" is load-bearing rather than vestigial: an
 * overseas recall is what refutes a claim of a Singapore recall.
 */
export type Jurisdiction = "Singapore" | "Overseas" | "Unknown";

/** Which of the three in-scope domains a claim belongs to. */
export type Domain = "legal" | "product_safety" | "policy" | "unknown";

/**
 * The status a claim asserts, positioned on a domain-specific ladder.
 * Escalation = the claim asserts a higher rung than evidence supports.
 */
export type StatusType =
  // legal ladder
  | "allegation"
  | "investigation"
  | "arrest"
  | "statement"
  | "charge"
  | "conviction"
  | "sentence"
  | "release"
  | "bail"
  // product safety ladder
  | "advisory"
  | "warning"
  | "overseas_recall"
  | "local_recall"
  | "ban"
  // policy ladder
  | "proposed"
  | "passed"
  | "effective"
  | "enforced"
  | "deadline"
  | "penalty"
  | "unknown";

/** How a single evidence document relates to a single claim. */
export type GradeLabel =
  | "supports"
  | "refutes"
  | "partially_supports"
  | "does_not_answer";

export interface EvidenceGrade {
  evidenceId: string;
  label: GradeLabel;
  rationale: string;
  score: number;
}

export interface Claim {
  id: string;
  text: string;
  /** The original sentence this claim was extracted from. */
  sourceSpan: string;
  statusType: StatusType;
  domain: Domain;
  jurisdiction: Jurisdiction;
  verdict: Verdict;
  confidence: number;
  keyReason: string;
  evidenceIds: string[];
  grades: EvidenceGrade[];
  /** True when the claim asserts a higher status rung than the evidence reaches. */
  isEscalation: boolean;
  /** e.g. "charge -> conviction". Present only when isEscalation. */
  escalationFrom?: string | null;
  escalationTo?: string | null;
}

export interface Evidence {
  id: string;
  title: string;
  publisher: string;
  tier: SourceTier;
  jurisdiction: Jurisdiction;
  publishedAt: string;
  url: string;
  snippet: string;
  statusAsserted: StatusType;
  /** Always true in MVP. Bundled evidence is hand-written sample data. */
  isMock: boolean;
  supportsClaimIds: string[];
  refutesClaimIds: string[];
}

/** One rung of the status ladder, present or conspicuously absent. */
export interface TimelineEntry {
  stage: StatusType;
  label: string;
  date?: string | null;
  found: boolean;
  description: string;
  evidenceIds: string[];
}

export interface PipelineStep {
  step: number;
  node: string;
  summary: string;
  durationMs: number;
  details: Record<string, unknown>;
}

export interface VerifyResponse {
  overallVerdict: Verdict;
  summary: string;
  confidence: number;
  lastChecked: string;
  claims: Claim[];
  evidence: Evidence[];
  timeline: TimelineEntry[];
  shareableCorrection: string;
  pipelineTrace: PipelineStep[];
  /** Banner text reminding the user that evidence is seeded sample data. */
  mockNotice: string;
}

export interface VerifyRequest {
  message: string;
}
