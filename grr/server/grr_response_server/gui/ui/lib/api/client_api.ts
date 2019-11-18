/**
 * @fileoverview The module provides mappings for GRR API protos (in JSON
 * format) into TypeScript interfaces. They are not indended to be
 * complete: only actually used fields are mapped.
 *
 * TODO(user): Using Protobuf-code generation insted of manually writing
 * interface definitions is preferable, but it's a non-trivial task, since code
 * generation should be supported by OpenSource build pipeline.
 */

/**
 * KnowledgeBase proto mapping.
 */
export declare interface ApiKnowledgeBase {
  readonly fqdn?: string;
  readonly os?: string;
}

/**
 * ClientLabel proto mapping.
 */
export declare interface ApiClientLabel {
  readonly owner?: string;
  readonly name?: string;
}

/**
 * ApiClient proto mapping.
 */
export declare interface ApiClient {
  readonly clientId?: string;
  readonly urn?: string;

  readonly fleetspeakEnabled?: boolean;

  readonly knowledgeBase?: ApiKnowledgeBase;

  readonly firstSeenAt?: string;
  readonly lastSeenAt?: string;
  readonly lastBootedAt?: string;
  readonly lastClock?: string;
  readonly labels: ReadonlyArray<ApiClientLabel>;
}

/**
 * ApiSearchClientArgs proto mapping.
 */
export declare interface ApiSearchClientArgs {
  readonly query?: string;
  readonly offset?: number;
  readonly count?: number;
}

/**
 * ApiSearchClientResult proto mapping.
 */
export declare interface ApiSearchClientResult {
  readonly items: ReadonlyArray<ApiClient>;
}
