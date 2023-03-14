import {ApiHunt, ApiHuntApproval, ApiHuntState, HuntRunnerArgs, OutputPluginDescriptor} from '../api/api_interfaces';
import {Hunt, HuntApproval, HuntState, HuntType, SafetyLimits} from '../models/hunt';
import {ResultKey, toResultKeyString} from '../models/result';
import {assertEnum, assertKeyNonNull, assertKeyTruthy, assertNumber} from '../preconditions';

import {createDate, createOptionalDate, createOptionalDuration} from './primitive';
import {translateApproval} from './user';

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

/** Translates from ApiHuntState enum to internal model HuntState enum. */
export function translateHuntState(hunt: ApiHunt): HuntState {
  switch (hunt.state) {
    case ApiHuntState.PAUSED:
      if (hunt.initStartTime) {
        return HuntState.PAUSED;
      }
      return HuntState.NOT_STARTED;
    case ApiHuntState.STARTED:
      return HuntState.RUNNING;
    case ApiHuntState.STOPPED:
      return HuntState.CANCELLED;
    case ApiHuntState.COMPLETED:
      return HuntState.COMPLETED;
    default:
      // Should be unreachable
      throw new Error(`Unknown ApiHuntState value: ${hunt.state}.`);
  }
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

  assertEnum(hunt.state, ApiHuntState);

  return {
    allClientsCount: BigInt(hunt.allClientsCount ?? 0),
    clientsWithResultsCount: BigInt(hunt.clientsWithResultsCount ?? 0),
    completedClientsCount: BigInt(hunt.completedClientsCount ?? 0),
    crashedClientsCount: BigInt(hunt.crashedClientsCount ?? 0),
    failedClientsCount: BigInt(hunt.failedClientsCount ?? 0),
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
    state: translateHuntState(hunt),
    stateComment: hunt.stateComment,
    totalCpuUsage: hunt.totalCpuUsage ?? 0,
    totalNetUsage: BigInt(hunt.totalNetUsage ?? 0),
    safetyLimits: translateSafetyLimits(hunt.huntRunnerArgs),
    flowReference: hunt.originalObject?.flowReference,
    huntReference: hunt.originalObject?.huntReference,
    clientRuleSet: hunt.clientRuleSet,
    outputPlugins: hunt.huntRunnerArgs.outputPlugins ?
        hunt.huntRunnerArgs.outputPlugins as OutputPluginDescriptor[] :
        [],
  };
}

/** Translates from ApiHuntApproval to internal HuntApproval model */
export function translateHuntApproval(approval: ApiHuntApproval): HuntApproval {
  const translatedApproval = translateApproval(approval);

  assertKeyTruthy(approval, 'subject');
  const {subject} = approval;
  assertKeyTruthy(subject, 'huntId');

  return {
    ...translatedApproval,
    huntId: subject.huntId,
    subject: translateHunt(subject),
  };
}

/** Builds a string result key for the hunt result. */
export function getHuntResultKey(
    result: {clientId?: string, timestamp?: string}, huntId: string): string {
  const key: ResultKey = {
    clientId: result.clientId ?? '',
    flowId: huntId,
    timestamp: result.timestamp ?? '',
  };
  return toResultKeyString(key);
}

/** Translates from HuntState enum to ApiHuntState enum. */
export function toApiHuntState(state: HuntState): ApiHuntState {
  switch (state) {
    case HuntState.NOT_STARTED:
      return ApiHuntState.PAUSED;
    case HuntState.PAUSED:
      return ApiHuntState.PAUSED;
    case HuntState.RUNNING:
      return ApiHuntState.STARTED;
    case HuntState.CANCELLED:
      return ApiHuntState.STOPPED;
    case HuntState.COMPLETED:
      return ApiHuntState.COMPLETED;
    default:
      // Should be unreachable
      throw new Error(`Unknown HuntState value: ${state}.`);
  }
}
