/** Data structure describing GRR user. */
export declare interface GrrUser {
  readonly name: string;
  readonly canaryMode: boolean;
  readonly huntApprovalRequired: boolean;
}

/**
 * Indicates that an Approval has been granted and is currently valid.
 */
export interface Valid {
  readonly type: 'valid';
}

/** Indicates that an Approval is pending approval from an approver. */
export interface Pending {
  readonly type: 'pending';
  readonly reason: string;
}

/** Indicates that an Approval had been granted, but is expired. */
export interface Expired {
  readonly type: 'expired';
  readonly reason: string;
}

/** Indicates that an Approval is invalid for other reasons. */
export interface Invalid {
  readonly type: 'invalid';
  readonly reason: string;
}

/** Status of an Approval. */
export type ApprovalStatus = Valid|Pending|Expired|Invalid;