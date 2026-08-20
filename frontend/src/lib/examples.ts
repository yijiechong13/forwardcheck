/**
 * The five seeded demo claims.
 *
 * Each is a **synthetic forwarded-style message derived from real Singapore
 * public information** — not a captured private message. They are written the
 * way such messages actually circulate: urgency markers, imperatives, and a
 * mix of true and overstated statements.
 *
 * Between them they cover the three ways a forwarded claim overstates:
 *   STATUS   — a rung it has not reached (investigated -> charged)
 *   SCOPE    — who or what is covered (one batch -> all products)
 *   MODALITY — how certain a consequence is (up to $5,000 -> automatic fine)
 */
export interface ExampleClaim {
  id: string;
  label: string;
  blurb: string;
  message: string;
}

export const EXAMPLE_CLAIMS: ExampleClaim[] = [
  {
    id: "cat-licensing",
    label: "Cat licensing",
    blurb: "A real deadline, an automatic fine that is not real",
    message:
      "From 1 Sept, HDB cat owners with more than 2 cats will automatically be fined $5,000 and AVS will remove the extra cats. All cats, including community cats, must be licensed by 31 Aug.",
  },
  {
    id: "cdc-vouchers",
    label: "CDC vouchers",
    blurb: "Right amount, wrong unit — household read as individual",
    message:
      "Every Singaporean will get $500 CDC vouchers in cash this month, including PRs. Must claim by Sunday or lose it.",
  },
  {
    id: "vaping-penalties",
    label: "Vaping penalties",
    blurb: "A real law change, an invented automatic jail term",
    message:
      "From 1 May 2026, anyone caught with vapes or Kpods will automatically go to jail for 10 years.",
  },
  {
    id: "formula-recall",
    label: "Milk powder recall",
    blurb: "A batch recall stretched to two entire brands",
    message:
      "All NAN and Dumex milk powder in Singapore has been recalled because it contains toxins. Don't buy any.",
  },
  {
    id: "calamine-recall",
    label: "Calamine lotion",
    blurb: "One affected batch reported as every bottle",
    message:
      "Guardian calamine lotion contains cadmium. Throw away all bottles immediately.",
  },
];
