/** Descriptor containing information about a flow class. */
export declare interface FlowDescriptor {
  readonly name: string;
  readonly friendlyName: string;
  readonly category: string;
  readonly defaultArgs: unknown;
}

/** Map from Flow name to FlowDescriptor. */
export type FlowDescriptorMap = ReadonlyMap<string, FlowDescriptor>;

/** Flow state enum to be used inside the Flow. */
export enum FlowState {
  UNSET = 0,
  RUNNING = 1,
  FINISHED = 2,
  ERROR = 3,
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
  readonly state: FlowState;
}

/** FlowResult represents a single flow result. */
export declare interface FlowResult {
  readonly payload: unknown;
  readonly tag: string;
  readonly timestamp: Date;
}

/**
 * FlowResultQuery encapsulates details of a flow results query. Queries
 * are used by flow details components to request data to show.
 */
export declare interface FlowResultsQuery {
  readonly flowId: string;
  readonly withType?: string;
  readonly withTag?: string;
  readonly offset: number;
  readonly count: number;
}

/** Represents a state of a flow result set. */
export enum FlowResultSetState {
  /** Flow result set is currently being fetched. */
  IN_PROGRESS,
  /** Flow result set is fully fetched. */
  FETCHED,
}

/**
 * FlowResultSet represents a result set returned in response to a
 * FlowResulsQuery.
 */
export declare interface FlowResultSet {
  readonly sourceQuery: FlowResultsQuery;
  readonly state: FlowResultSetState;
  readonly items: ReadonlyArray<FlowResult>;
}

/** Single flow entry in the flows list. */
export declare interface FlowListEntry {
  readonly flow: Flow;
  readonly resultSets: FlowResultSet[];
}

/**
 * Updates (by returning a modified copy) a flow list entry with a given
 * result set. Result sets are effectively identified by their withTag/withType
 * combination. I.e. a result set with
 * withTag=undefined/withType=undefined/offset=0/count=100 is different from the
 * one with withTag=someTag/withType=undefined/offset=0/count=100, but is
 * replaceable by withTag=undefined/withType=undefined/offset=100/count=100.
 */
export function updateFlowListEntryResultSet(
    fle: FlowListEntry, resultSet: FlowResultSet): FlowListEntry {
  const newResultSets: FlowResultSet[] = [];
  let pushed = false;
  for (const rs of fle.resultSets) {
    if (rs.sourceQuery.withTag === resultSet.sourceQuery.withTag &&
        rs.sourceQuery.withType === resultSet.sourceQuery.withType) {
      newResultSets.push(resultSet);
      pushed = true;
    } else {
      newResultSets.push(rs);
    }
  }

  if (!pushed) {
    newResultSets.push(resultSet);
  }

  return {
    ...fle,
    resultSets: newResultSets,
  };
}

/** In a given FlowListEntry, find a result set matching given criteria. */
export function findFlowListEntryResultSet(
    fle: FlowListEntry,
    withType?: string,
    withTag?: string,
    ): FlowResultSet|undefined {
  return fle.resultSets.find(
      rs => rs.sourceQuery.withType === withType &&
          rs.sourceQuery.withTag === withTag);
}

/** Creates a default flow list entry from a given flow. */
export function flowListEntryFromFlow(flow: Flow): FlowListEntry {
  return {
    flow,
    resultSets: [],
  };
}

/** A scheduled flow, to be executed after approval has been granted. */
export declare interface ScheduledFlow {
  readonly scheduledFlowId: string;
  readonly clientId: string;
  readonly creator: string;
  readonly flowName: string;
  readonly flowArgs: unknown;
  readonly createTime: Date;
  readonly error?: string;
}
