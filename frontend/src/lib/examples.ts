/**
 * The three seeded demo claims.
 *
 * These are the messages the pipeline is tuned and evaluated against.
 * Each is written the way it actually circulates: forwarding cruft, emoji,
 * urgency markers, and a mix of true and escalated statements.
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
    id: "ns-enlistment",
    label: "NS legal status",
    blurb: "Charged, but the forward says convicted and sentenced",
    message:
      "BREAKING: Amos Yee has been sentenced to 3 years jail in Singapore after being deported from the US. He was arrested at Changi Airport and convicted under the Enlistment Act for NS offences. This means all NS defaulters who return from overseas will automatically be jailed. Forward this.",
  },
  {
    id: "rocky-case",
    label: "Developing news",
    blurb: "An investigation reported as a charge already in court",
    message:
      "Rocky's owner has been charged with animal abuse after the dog died during an enforcement operation. The owner is already facing court action. Forward this.",
  },
];
