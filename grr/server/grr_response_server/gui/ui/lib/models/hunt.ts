import {
  ApiFlowReference,
  ApiHuntReference,
  ApiHuntStateReason,
  ForemanClientRuleSet,
  OutputPluginDescriptor,
} from '../api/api_interfaces';
import {Duration} from '../date_time';

import {getFlowTitleFromFlowName} from './flow';
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
  readonly created: Date;
  readonly creator: string;
  readonly description: string;
  readonly duration?: Duration;
  readonly flowArgs?: unknown;
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
  readonly outputPlugins?: OutputPluginDescriptor[];
  readonly resourceUsage?: HuntResourceUsage;
}

/** Approval proto mapping. */
export declare interface HuntApproval extends Approval {
  readonly huntId: string;
  readonly subject: Hunt;
}

/** ApprovalRequest for hunt */
export interface HuntApprovalRequest extends ApprovalRequest {
  readonly huntId: string;
}

/** Data format for rows in the Hunt Completion Progress table */
export interface HuntCompletionProgressTableRow {
  timestamp: number;
  completedClients?: bigint;
  scheduledClients?: bigint;
  completedClientsPct?: bigint;
  scheduledClientsPct?: bigint;
}

/** Gets the hunt title to be displayed across different pages */
export function getHuntTitle(hunt: Hunt | null): string {
  const name = hunt?.name === 'GenericHunt' ? '' : hunt?.name;
  return (
    hunt?.description ||
    name ||
    'Untitled fleet collection' +
      (hunt?.flowName ? ': ' + getFlowTitleFromFlowName(hunt.flowName) : '')
  );
}
