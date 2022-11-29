import {ApiHunt, ApiHuntApproval, ApiHuntResult, ApiHuntState, HuntRunnerArgs} from '../api/api_interfaces';
import {Hunt, HuntApproval, HuntState, HuntType, SafetyLimits} from '../models/hunt';
import {ResultKey, toResultKeyString} from '../models/result';
import {assertEnum, assertKeyNonNull, assertNumber} from '../preconditions';

import {createDate, createOptionalDate, createOptionalDuration} from './primitive';
import {translateApprovalStatus} from './user';

const TWO_WEEKS = 2 * 7 * 24 * 60 * 60;

/** Constructs a SafetyLimits from the HuntRunnerArgs */
export function translateSafetyLimits(args: HuntRunnerArgs): SafetyLimits {
  assertNumber(args.clientRate);

  return {
    clientRate: args.clientRate,
    clientLimit: BigInt(args.clientLimit ?? '0'),
    crashLimit: BigInt(args.crashLimit ?? '0'),
    avgResultsPerClientLimit: BigInt(args.avgResultsPerClientLimit ?? '0'),
    avgCpuSecondsPerClientLimit:
        BigInt(args.avgCpuSecondsPerClientLimit ?? '0'),
    avgNetworkBytesPerClientLimit:
        BigInt(args.avgNetworkBytesPerClientLimit ?? '0'),
    cpuLimit: BigInt(args.cpuLimit ?? '0'),
    expiryTime: BigInt(args.expiryTime ?? TWO_WEEKS),
    networkBytesLimit: BigInt(args.networkBytesLimit ?? '0'),
  };
}

/** Translates from ApiHunt to internal Hunt model. */
export function translateHunt(hunt: ApiHunt): Hunt {
  assertKeyNonNull(hunt, 'created');
  assertKeyNonNull(hunt, 'creator');
  assertKeyNonNull(hunt, 'huntId');
  assertKeyNonNull(hunt, 'name');
  assertKeyNonNull(hunt, 'state');
  assertKeyNonNull(hunt, 'huntRunnerArgs');

  const huntType = hunt.huntType ?? HuntType.UNSET;
  assertEnum(huntType, HuntType);

  assertEnum(hunt.state, HuntState);

  return {
    allClientsCount: BigInt(hunt.allClientsCount ?? 0),
    clientsWithResultsCount: BigInt(hunt.clientsWithResultsCount ?? 0),
    completedClientsCount: BigInt(hunt.completedClientsCount ?? 0),
    created: createDate(hunt.created),
    creator: hunt.creator,
    description: hunt.description ?? '',
    duration: createOptionalDuration(hunt.duration),
    flowArgs: hunt.flowArgs,
    flowName: hunt.flowName,
    huntId: hunt.huntId,
    huntType,
    initStartTime: createOptionalDate(hunt.initStartTime),
    internalError: hunt.internalError,
    isRobot: hunt.isRobot ?? false,
    lastStartTime: createOptionalDate(hunt.lastStartTime),
    name: hunt.name,
    remainingClientsCount: BigInt(hunt.remainingClientsCount ?? 0),
    resultsCount: BigInt(hunt.resultsCount ?? 0),
    state: hunt.state,
    totalCpuUsage: hunt.totalCpuUsage ?? 0,
    totalNetUsage: BigInt(hunt.totalNetUsage ?? 0),
    safetyLimits: translateSafetyLimits(hunt.huntRunnerArgs),
    flowReference: hunt.originalObject?.flowReference,
    huntReference: hunt.originalObject?.huntReference,
    clientRuleSet: hunt.clientRuleSet,
  };
}

/** Translates from ApiHuntApproval to internal HuntApproval model */
export function translateHuntApproval(approval: ApiHuntApproval): HuntApproval {
  assertKeyNonNull(approval, 'id');
  assertKeyNonNull(approval, 'subject');
  assertKeyNonNull(approval, 'reason');
  assertKeyNonNull(approval, 'requestor');

  const {subject} = approval;
  assertKeyNonNull(subject, 'huntId');

  const status =
      translateApprovalStatus(approval.isValid, approval.isValidMessage);

  return {
    status,
    approvalId: approval.id,
    huntId: subject.huntId,
    reason: approval.reason,
    requestedApprovers: approval.notifiedUsers ?? [],
    approvers: (approval.approvers ?? []).filter(u => u !== approval.requestor),
    requestor: approval.requestor,
    subject: translateHunt(approval.subject),
  };
}

/** Builds a string result key for the hunt result. */
export function getHuntResultKey(
    result: ApiHuntResult, huntId: string): string {
  const key: ResultKey = {
    clientId: result.clientId ?? '',
    flowId: huntId,
    timestamp: result.timestamp ?? '',
  };
  return toResultKeyString(key);
}

/** Translates from HuntState enum to ApiHuntState enum. */
export function toApiHuntState(state: HuntState): ApiHuntState {
  assertEnum(state, ApiHuntState);
  return state;
}
