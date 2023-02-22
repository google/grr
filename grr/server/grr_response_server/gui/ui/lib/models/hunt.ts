import {ApiFlowReference, ApiHuntReference, ForemanClientRuleSet, OutputPluginDescriptor} from '../api/api_interfaces';
import {Duration} from '../date_time';

import {Approval, ApprovalRequest} from './user';

/** Key used to identify a hunt approval */
export interface HuntApprovalKey {
  readonly huntId: string;
  readonly approvalId: string;
  readonly requestor: string;
}

/** Safety limits of a new hunt */
export declare interface SafetyLimits {
  readonly cpuLimit: bigint;
  readonly networkBytesLimit: bigint;
  readonly clientRate: number;
  readonly crashLimit: bigint;
  readonly avgResultsPerClientLimit: bigint;
  readonly avgCpuSecondsPerClientLimit: bigint;
  readonly avgNetworkBytesPerClientLimit: bigint;
  readonly expiryTime: bigint;
  readonly clientLimit: bigint;
}

/** ApiHunt.State proto mapping. */
export enum HuntState {
  NOT_STARTED = 'NOT_STARTED',
  PAUSED = 'PAUSED',
  RUNNING = 'RUNNING',
  CANCELLED = 'CANCELLED',
  COMPLETED = 'COMPLETED',
}

/** ApiHunt.HuntType proto mapping. */
export enum HuntType {
  UNSET = 'UNSET',
  STANDARD = 'STANDARD',
  VARIABLE = 'VARIABLE',
}

/** Hunt proto mapping. */
export declare interface Hunt {
  readonly allClientsCount: bigint;
  readonly clientsWithResultsCount: bigint;
  readonly completedClientsCount: bigint;
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
  readonly stateComment?: string;
  readonly totalCpuUsage: number;
  readonly totalNetUsage: bigint;
  readonly safetyLimits: SafetyLimits;
  readonly flowReference?: ApiFlowReference;
  readonly huntReference?: ApiHuntReference;
  readonly clientRuleSet?: ForemanClientRuleSet;
  readonly outputPlugins?: OutputPluginDescriptor[];
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
