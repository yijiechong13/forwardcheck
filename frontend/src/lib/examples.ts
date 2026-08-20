/**
 * The four seeded demo claims.
 *
 * One per status domain, chosen so each exercises a different escalation:
 * policy scope and penalty, legal rung, product-safety jurisdiction and scope,
 * and policy stage. Each is written the way it actually circulates — forwarding
 * cruft, emoji, urgency markers, and a mix of true and escalated statements.
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
    label: "HDB cat licensing",
    blurb: "A real deadline wrapped in a penalty that is not real",
    message:
      "⚠️ URGENT ⚠️ From 1 Sept, HDB cat owners with more than 2 cats will be fined $5,000 and AVS will remove the extra cats. All cats, including community cats, must be licensed by 31 Aug. Please forward to all cat owners 🐱🙏",
  },
  {
    id: "rocky-case",
    label: "Charged, or investigated?",
    blurb: "An investigation reported as a charge already in court",
    message:
      "Rocky's owner has been charged with animal abuse after the dog died during an enforcement operation. The owner is already facing court action. Forward this.",
  },
  {
    id: "product-recall",
    label: "Product recall",
    blurb: "An overseas batch recall reported as a Singapore-wide one",
    message:
      "URGENT: This snack product has been recalled in Singapore and taken off all shelves. The whole product line is affected. Please forward to your family.",
  },
  {
    id: "policy-stage",
    label: "Policy in force?",
    blurb: "A law that passed, reported as already enforced",
    message:
      "The new workplace fairness law has passed and fines start immediately. Employers who discriminate will be fined from this month. Forward this.",
  },
];
