export const MAPPING_ROW_STATUSES = [
  "proposed",
  "needs_review",
  "changed_from_published",
  "approved",
  "rejected",
  "ignored",
] as const;

export type MappingRowStatus = (typeof MAPPING_ROW_STATUSES)[number];

export const SAMPLE_RUN_REVIEW_STATUSES = ["approved", "needs_review", "rejected"] as const;

export type SampleRunReviewStatus = (typeof SAMPLE_RUN_REVIEW_STATUSES)[number];
