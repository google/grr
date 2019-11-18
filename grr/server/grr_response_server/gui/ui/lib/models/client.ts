/**
 * @fileoverview The module provides client-related data model entities.
 */

/**
 * Client's knowledge base data.
 */
export interface KnowledgeBase {
  /** Client's FQDN. */
  readonly fqdn?: string;
  readonly os?: string;
}

/**
 * Client Label.
 */
export interface ClientLabel {
  readonly owner: string;
  readonly name: string;
}

/**
 * Client.
 */
export interface Client {
  /** Client id. */
  readonly clientId: string;
  /** Whether the client communicates with GRR through Fleetspeak. */
  readonly fleetspeakEnabled: boolean;
  /** Client's knowledge base. */
  readonly knowledgeBase: KnowledgeBase;
  // TODO(user): Replace `Date` type with immutable date type.
  /** When the client was first seen. */
  readonly firstSeenAt?: Date;
  /** When the client was last seen. */
  readonly lastSeenAt?: Date;
  /** Last time the client booted. */
  readonly lastBootedAt?: Date;
  /** Last reported client clock time. */
  readonly lastClock?: Date;
  /** List of ClientLabels */
  readonly labels: ReadonlyArray<ClientLabel>;
}
