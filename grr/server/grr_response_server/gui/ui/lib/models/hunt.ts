import {
  ApiFlowReference,
  ApiHuntReference,
  ApiHuntStateReason,
  ForemanClientRuleSet,
} from '../api/api_interfaces';
import {Duration} from '../date_time';

import {ApiListHuntsArgsRobotFilter} from '../api/api_interfaces';
import {FlowType, isFlowResult} from './flow';
import {OutputPlugin} from './output_plugin';
import {CollectionResult} from './result';
import {Approval, ApprovalRequest} from './user';

/** Key used to identify a hunt approval */
export interface HuntApprovalKey {
  readonly huntId: string;
  readonly approvalId: string;
  readonly requestor: string;
}

/** Safety limits of a new hunt */
export declare interface SafetyLimits {
  readonly clientRate: number;

  // Completes hunt
  readonly expiryTime: bigint;

  // Pauses hunt
  readonly clientLimit: bigint;

  // Stops hunt
  readonly crashLimit: bigint;
  readonly avgResultsPerClientLimit: bigint;
  readonly avgCpuSecondsPerClientLimit: bigint;
  readonly avgNetworkBytesPerClientLimit: bigint;

  // Stops flow:
  readonly perClientCpuLimit: bigint;
  readonly perClientNetworkBytesLimit: bigint;
}

/** Arguments for listing hunts. */
export interface ListHuntsArgs {
  readonly count?: number;
  readonly offset?: number;
  readonly robotFilter?: ApiListHuntsArgsRobotFilter;
  readonly stateFilter?: HuntState;
}

/** ApiHunt.State proto mapping. */
export enum HuntState {
  NOT_STARTED = 'NOT_STARTED',
  RUNNING = 'RUNNING',
  REACHED_CLIENT_LIMIT = 'REACHED_CLIENT_LIMIT',
  CANCELLED = 'CANCELLED',
  REACHED_TIME_LIMIT = 'REACHED_TIME_LIMIT',
}

/** ApiHunt.HuntType proto mapping. */
export enum HuntType {
  UNSET = 'UNSET',
  STANDARD = 'STANDARD',
  VARIABLE = 'VARIABLE',
}

/** Resource Usage for this hunt. */
export declare interface HuntResourceUsage {
  totalCPUTime?: number; // This can be a float
  totalNetworkTraffic?: bigint;
}

/** Hunt proto mapping. */
export declare interface Hunt {
  readonly allClientsCount: bigint;
  readonly clientsWithResultsCount: bigint;
  readonly completedClientsCount: bigint;
  readonly crashedClientsCount: bigint;
  readonly failedClientsCount: bigint;
  // When creating a new hunt, the response does not contain the created field.
  readonly created: Date | undefined;
  readonly creator: string;
  readonly description: string;
  readonly duration?: Duration;
  readonly flowArgs?: unknown;
  readonly flowType?: FlowType;
  readonly flowName?: string;
  readonly huntId: string;
  readonly huntType: HuntType;
  readonly initStartTime?: Date;
  readonly internalError?: string;
  readonly isRobot: boolean;
  readonly lastStartTime?: Date;
  readonly name: string;
  readonly remainingClientsCount: bigint;
  readonly resultsCount: bigint;
  readonly state: HuntState;
  readonly stateReason: ApiHuntStateReason;
  readonly stateComment?: string;
  readonly safetyLimits: SafetyLimits;
  readonly flowReference?: ApiFlowReference;
  readonly huntReference?: ApiHuntReference;
  readonly clientRuleSet?: ForemanClientRuleSet;
  readonly outputPlugins?: OutputPlugin[];
  readonly resourceUsage?: HuntResourceUsage;
}

/** Arguments for listing hunt results. */
export declare interface ListHuntResultsArgs {
  readonly huntId: string;
  readonly offset?: number;
  readonly count?: number;
  readonly filter?: string;
  readonly withType?: string;
}

/** Arguments for listing hunt errors. */
export declare interface ListHuntErrorsArgs {
  readonly huntId: string;
  readonly offset?: number;
  readonly count?: number;
  readonly filter?: string;
}

/** HuntResult represents a single hunt result. */
export declare interface HuntResult extends CollectionResult {}

/** Type guard for HuntResult. */
export function isHuntResult(result: CollectionResult): result is HuntResult {
  return !isFlowResult(result);
}

/** HuntError represents a single hunt error. */
export declare interface HuntError {
  readonly clientId: string;
  readonly logMessage?: string;
  readonly backtrace?: string;
  readonly timestamp: Date;
}

/**
 * ListHuntResultsResult represents a list of hunt results and the total count.
 */
export declare interface ListHuntResultsResult {
  readonly totalCount: number | undefined;
  readonly results: readonly HuntResult[];
}

/**
 * ListHuntErrorsResult represents a list of hunt errors and the total count.
 */
export declare interface ListHuntErrorsResult {
  readonly totalCount: number | undefined;
  readonly errors: readonly HuntError[];
}

/** Result of listing hunts. */
export declare interface ListHuntsResult {
  readonly hunts: Hunt[];
  readonly totalCount?: number;
}

/** Approval proto mapping. */
export declare interface HuntApproval extends Approval {
  readonly huntId: string;
  readonly subject: Hunt;
}

/** Type guard for HuntApproval. */
export function isHuntApproval(approval: Approval): approval is HuntApproval {
  return (approval as HuntApproval).huntId !== undefined;
}

/** ApprovalRequest for hunt */
export interface HuntApprovalRequest extends ApprovalRequest {
  readonly huntId: string;
}

/** HuntLog proto mapping. */
export declare interface HuntLog {
  readonly clientId?: string;
  readonly logMessage?: string;
  readonly flowName?: string;
  readonly flowId?: string;
  readonly timestamp?: Date;
}

/** Result of listing hunt logs. */
export declare interface ListHuntLogsResult {
  readonly logs: readonly HuntLog[];
  readonly totalCount?: number;
}
