/**
 * A complete, hand-written `VerifyResponse` fixture.
 *
 * Phase 1 rendered the UI from this; since Phase 2 the page calls the real API.
 * It is kept deliberately: it documents the full response shape in one readable
 * place, and lets the UI be developed or storybooked without running uvicorn.
 * Not imported by the app — import it in a component harness when you need it.
 */
import type { VerifyResponse } from "./types";

const MOCK_NOTICE =
  "Evidence shown is seeded sample data for demonstration. URLs are placeholders, not real citations.";

export const MOCK_CAT_LICENSING: VerifyResponse = {
  overallVerdict: "Misleading",
  summary:
    "The licensing deadline in this message is real, but the penalty and enforcement claims are not. The $5,000 figure is the maximum court fine under the Animals and Birds Act, not an automatic fine for owning three cats, and there is no evidence that AVS removes cats from compliant households. Community cats are not covered by the pet licensing scheme.",
  confidence: 0.82,
  lastChecked: "2026-08-20T05:14:22Z",
  mockNotice: MOCK_NOTICE,
  claims: [
    {
      id: "c1",
      text: "Pet cats in HDB flats must be licensed by 31 August.",
      sourceSpan: "All cats, including community cats, must be licensed by 31 Aug.",
      statusType: "deadline",
      domain: "policy",
      jurisdiction: "Singapore",
      verdict: "Supported",
      confidence: 0.91,
      keyReason:
        "AVS licensing scheme confirms a licensing requirement for pet cats with the stated deadline.",
      evidenceIds: ["e1", "e2"],
      grades: [
        {
          evidenceId: "e1",
          label: "supports",
          rationale: "States the pet cat licensing deadline directly.",
          score: 0.93,
        },
        {
          evidenceId: "e2",
          label: "partially_supports",
          rationale: "Confirms the scheme exists but does not restate the date.",
          score: 0.61,
        },
      ],
      isEscalation: false,
      escalationFrom: null,
      escalationTo: null,
    },
    {
      id: "c2",
      text: "Owners with more than 2 cats will be fined $5,000.",
      sourceSpan:
        "HDB cat owners with more than 2 cats will be fined $5,000",
      statusType: "penalty",
      domain: "policy",
      jurisdiction: "Singapore",
      verdict: "Misleading",
      confidence: 0.86,
      keyReason:
        "$5,000 is the maximum penalty a court may impose, not an automatic fine. Evidence describes a transition period for existing multi-cat households rather than immediate fines.",
      evidenceIds: ["e3", "e4"],
      grades: [
        {
          evidenceId: "e3",
          label: "refutes",
          rationale:
            "Describes $5,000 as a maximum court penalty, contradicting 'will be fined'.",
          score: 0.88,
        },
        {
          evidenceId: "e4",
          label: "refutes",
          rationale:
            "States existing owners above the cap may keep their cats under a transition arrangement.",
          score: 0.79,
        },
      ],
      isEscalation: true,
      escalationFrom: "maximum penalty",
      escalationTo: "automatic fine",
    },
    {
      id: "c3",
      text: "AVS will remove the extra cats from owners exceeding the cap.",
      sourceSpan: "AVS will remove the extra cats",
      statusType: "enforced",
      domain: "policy",
      jurisdiction: "Singapore",
      verdict: "Insufficient evidence",
      confidence: 0.34,
      keyReason:
        "No retrieved source describes confiscation or removal of cats as an enforcement action under this scheme.",
      evidenceIds: ["e4"],
      grades: [
        {
          evidenceId: "e4",
          label: "does_not_answer",
          rationale:
            "Covers transition arrangements but is silent on removal or confiscation.",
          score: 0.42,
        },
      ],
      isEscalation: false,
      escalationFrom: null,
      escalationTo: null,
    },
    {
      id: "c4",
      text: "Community cats must be licensed.",
      sourceSpan: "All cats, including community cats, must be licensed",
      statusType: "effective",
      domain: "policy",
      jurisdiction: "Singapore",
      verdict: "Misleading",
      confidence: 0.8,
      keyReason:
        "The licensing scheme applies to owned pet cats. Community cats without an owner are handled under a separate programme.",
      evidenceIds: ["e5"],
      grades: [
        {
          evidenceId: "e5",
          label: "refutes",
          rationale:
            "Explicitly scopes licensing to owned pet cats and excludes community cats.",
          score: 0.85,
        },
      ],
      isEscalation: true,
      escalationFrom: "pet cats in scope",
      escalationTo: "all cats in scope",
    },
  ],
  evidence: [
    {
      id: "e1",
      title: "Cat Licensing Scheme: registration opens for pet cat owners",
      publisher: "Animal & Veterinary Service (AVS), NParks",
      tier: "official",
      jurisdiction: "Singapore",
      publishedAt: "2026-06-02",
      url: "https://www.avs.nparks.gov.sg/[sample-placeholder]",
      snippet:
        "Pet cat owners are required to license their cats. Licences may be obtained online at no cost during the initial registration window, which closes on 31 August.",
      statusAsserted: "deadline",
      isMock: true,
      supportsClaimIds: ["c1"],
      refutesClaimIds: [],
    },
    {
      id: "e2",
      title: "Cat management framework announced following public consultation",
      publisher: "Ministry of National Development",
      tier: "official",
      jurisdiction: "Singapore",
      publishedAt: "2026-05-20",
      url: "https://www.mnd.gov.sg/[sample-placeholder]",
      snippet:
        "The framework introduces licensing for pet cats and lifts the previous prohibition on cats in HDB flats, subject to conditions on the number of cats per household.",
      statusAsserted: "passed",
      isMock: true,
      supportsClaimIds: ["c1"],
      refutesClaimIds: [],
    },
    {
      id: "e3",
      title: "Animals and Birds Act — penalties for licensing offences",
      publisher: "Singapore Statutes Online",
      tier: "primary",
      jurisdiction: "Singapore",
      publishedAt: "2026-01-15",
      url: "https://sso.agc.gov.sg/[sample-placeholder]",
      snippet:
        "A person guilty of an offence under this section shall be liable on conviction to a fine not exceeding $5,000. The penalty is a maximum determined by the court on conviction.",
      statusAsserted: "penalty",
      isMock: true,
      supportsClaimIds: [],
      refutesClaimIds: ["c2"],
    },
    {
      id: "e4",
      title: "FAQ: households with more than the permitted number of cats",
      publisher: "Animal & Veterinary Service (AVS), NParks",
      tier: "official",
      jurisdiction: "Singapore",
      publishedAt: "2026-06-02",
      url: "https://www.avs.nparks.gov.sg/[sample-placeholder-faq]",
      snippet:
        "Existing owners who have more cats than the cap at the start of the scheme may continue to keep them, provided all cats are licensed. Owners are not required to give up their cats.",
      statusAsserted: "effective",
      isMock: true,
      supportsClaimIds: [],
      refutesClaimIds: ["c2"],
    },
    {
      id: "e5",
      title: "Community cats and the licensing scheme",
      publisher: "Animal & Veterinary Service (AVS), NParks",
      tier: "official",
      jurisdiction: "Singapore",
      publishedAt: "2026-06-10",
      url: "https://www.avs.nparks.gov.sg/[sample-placeholder-community]",
      snippet:
        "Licensing applies to owned pet cats. Community cats, which do not have an owner, are managed under a separate sterilisation and care programme and do not require a licence.",
      statusAsserted: "effective",
      isMock: true,
      supportsClaimIds: [],
      refutesClaimIds: ["c4"],
    },
  ],
  timeline: [
    {
      stage: "proposed",
      label: "Proposed",
      date: "2025-09-01",
      found: true,
      description: "Public consultation opened on a cat management framework.",
      evidenceIds: ["e2"],
    },
    {
      stage: "passed",
      label: "Passed / announced",
      date: "2026-05-20",
      found: true,
      description: "Framework announced following consultation.",
      evidenceIds: ["e2"],
    },
    {
      stage: "effective",
      label: "In effect",
      date: "2026-06-02",
      found: true,
      description: "Licensing registration opened for pet cat owners.",
      evidenceIds: ["e1", "e4"],
    },
    {
      stage: "deadline",
      label: "Deadline",
      date: "2026-08-31",
      found: true,
      description: "Close of the initial registration window.",
      evidenceIds: ["e1"],
    },
    {
      stage: "enforced",
      label: "Enforcement action",
      date: null,
      found: false,
      description:
        "No evidence of fines issued or cats removed under this scheme.",
      evidenceIds: [],
    },
  ],
  shareableCorrection:
    "Mostly misleading. Pet cat licensing by 31 Aug is real — but the $5,000 figure is the MAXIMUM court fine, not an automatic penalty for having 3 cats. Existing owners above the cap can keep their cats if licensed. AVS is not removing cats. Community cats don't need licences. Please don't forward the original.",
  pipelineTrace: [
    {
      step: 1,
      node: "normalise",
      summary: "Stripped forwarding markers and emoji, normalised 2 date references",
      durationMs: 3,
      details: {
        removed: ["⚠️ URGENT ⚠️", "Please forward to all cat owners", "🐱🙏"],
        datesNormalised: { "1 Sept": "2026-09-01", "31 Aug": "2026-08-31" },
        charsBefore: 232,
        charsAfter: 168,
      },
    },
    {
      step: 2,
      node: "decompose",
      summary: "Extracted 4 atomic claims from 2 sentences",
      durationMs: 7,
      details: {
        claimIds: ["c1", "c2", "c3", "c4"],
        droppedNonCheckable: ["Please forward to all cat owners"],
      },
    },
    {
      step: 3,
      node: "route",
      summary: "All 4 claims routed to domain=policy, jurisdiction=Singapore",
      durationMs: 2,
      details: {
        c1: "deadline/policy",
        c2: "penalty/policy",
        c3: "enforced/policy",
        c4: "effective/policy",
      },
    },
    {
      step: 4,
      node: "retrieve",
      summary: "Retrieved 5 documents across 4 claims (tier-weighted lexical)",
      durationMs: 11,
      details: {
        c1: ["e1", "e2"],
        c2: ["e3", "e4"],
        c3: ["e4"],
        c4: ["e5"],
        storeSize: 18,
      },
    },
    {
      step: 5,
      node: "grade",
      summary: "6 grades: 1 supports, 4 refutes/partial, 1 does-not-answer",
      durationMs: 9,
      details: {
        supports: 1,
        partially_supports: 1,
        refutes: 3,
        does_not_answer: 1,
      },
    },
    {
      step: 6,
      node: "freshness",
      summary: "All evidence within 6 months; no stale sources",
      durationMs: 1,
      details: { oldestDoc: "2026-01-15", staleThresholdDays: 540, staleCount: 0 },
    },
    {
      step: 7,
      node: "verdict",
      summary:
        "Overall Misleading — 2 escalations detected, 1 abstention, 1 supported",
      durationMs: 4,
      details: {
        perClaim: {
          c1: "Supported",
          c2: "Misleading",
          c3: "Insufficient evidence",
          c4: "Misleading",
        },
        rule: "any Misleading/False present and >=1 Supported -> overall Misleading",
      },
    },
  ],
};
