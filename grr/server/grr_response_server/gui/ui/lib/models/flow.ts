/** Descriptor containing information about a flow class. */
export declare interface FlowDescriptor {
  readonly name: string;
  readonly friendlyName: string;
  readonly category: string;
  readonly defaultArgs: unknown;
}

/** A Flow is a server-side process that collects data from clients. */
export declare interface Flow {
  readonly flowId: string;
  readonly clientId: string;
  readonly lastActiveAt: Date;
  readonly startedAt: Date;
  readonly name: string;
  readonly creator: string;
  readonly args: unknown|undefined;
  readonly progress: unknown|undefined;
}

/** Single flow entry in the flows list. */
export declare interface FlowListEntry {
  readonly flow: Flow;
  readonly isExpanded: boolean;
}

/** Creates a default flow list entry from a given flow. */
export function flowListEntryFromFlow(flow: Flow): FlowListEntry {
  return {
    flow,
    isExpanded: false,
  };
}
