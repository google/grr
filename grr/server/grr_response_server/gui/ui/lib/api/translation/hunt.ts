import {
  Hunt,
  HuntApproval,
  HuntError,
  HuntLog,
  HuntResult,
  HuntState,
  HuntType,
  ListHuntErrorsArgs,
  ListHuntErrorsResult,
  ListHuntLogsResult,
  ListHuntResultsArgs,
  ListHuntResultsResult,
  ListHuntsArgs,
  ListHuntsResult,
  SafetyLimits,
} from '../../models/hunt';
import {typeUrlToPayloadType} from '../../models/result';
import {
  assertEnum,
  assertKeyNonNull,
  assertKeyTruthy,
  assertNumber,
} from '../../preconditions';
import {checkExhaustive} from '../../utils';
import {
  ApiHunt,
  ApiHuntApproval,
  ApiHuntError,
  ApiHuntLog,
  ApiHuntResult,
  ApiHuntState,
  ApiHuntStateReason,
  ApiListHuntErrorsArgs,
  ApiListHuntErrorsResult,
  ApiListHuntLogsResult,
  ApiListHuntResultsArgs,
  ApiListHuntResultsResult,
  ApiListHuntsArgs,
  ApiListHuntsResult,
  HuntRunnerArgs,
} from '../api_interfaces';
import {translateApiFlowType} from './flow';
import {translateOutputPlugin} from './output_plugin';
import {
  createDate,
  createOptionalDate,
  createOptionalDuration,
  createUnknownObject,
} from './primitive';
import {translateApproval} from './user';

const TWO_WEEKS = 2 * 7 * 24 * 60 * 60;

/** Constructs a SafetyLimits from the HuntRunnerArgs */
export function translateSafetyLimits(args: HuntRunnerArgs): SafetyLimits {
  assertNumber(args.clientRate);

  return {
    clientRate: args.clientRate,
    clientLimit: BigInt(args.clientLimit ?? '0'),
    crashLimit: BigInt(args.crashLimit ?? '0'),

    expiryTime: BigInt(args.expiryTime ?? TWO_WEEKS),

    avgResultsPerClientLimit: BigInt(args.avgResultsPerClientLimit ?? '0'),
    avgCpuSecondsPerClientLimit: BigInt(
      args.avgCpuSecondsPerClientLimit ?? '0',
    ),
    avgNetworkBytesPerClientLimit: BigInt(
      args.avgNetworkBytesPerClientLimit ?? '0',
    ),

    perClientCpuLimit: BigInt(args.perClientCpuLimit ?? '0'),
    perClientNetworkBytesLimit: BigInt(args.perClientNetworkLimitBytes ?? '0'),
  };
}

/** Translates from ApiHuntState enum to internal model HuntState enum. */
export function translateHuntState(
  state: ApiHuntState,
  initStartTime?: string,
): HuntState {
  switch (state) {
    case ApiHuntState.PAUSED:
      if (initStartTime) {
        return HuntState.REACHED_CLIENT_LIMIT;
      }
      return HuntState.NOT_STARTED;
    case ApiHuntState.STARTED:
      return HuntState.RUNNING;
    case ApiHuntState.STOPPED:
      return HuntState.CANCELLED;
    case ApiHuntState.COMPLETED:
      return HuntState.REACHED_TIME_LIMIT;
    default:
      checkExhaustive(state);
  }
}

/** Translates from internal model HuntState enum to ApiHuntState enum. */
export function toApiHuntState(state: HuntState): ApiHuntState {
  switch (state) {
    case HuntState.NOT_STARTED:
      return ApiHuntState.PAUSED;
    case HuntState.RUNNING:
      return ApiHuntState.STARTED;
    case HuntState.REACHED_CLIENT_LIMIT:
      return ApiHuntState.PAUSED;
    case HuntState.CANCELLED:
      return ApiHuntState.STOPPED;
    case HuntState.REACHED_TIME_LIMIT:
      return ApiHuntState.COMPLETED;
    default:
      checkExhaustive(state);
  }
}

/** Translates from internal model ListHuntsArgs to ApiListHuntsArgs. */
export function toApiListHuntsArgs(args: ListHuntsArgs): ApiListHuntsArgs {
  return {
    count: args.count ? String(args.count) : undefined,
    offset: args.offset ? String(args.offset) : undefined,
    robotFilter: args.robotFilter ?? undefined,
    withState: args.stateFilter ? toApiHuntState(args.stateFilter) : undefined,
  };
}

/** Translates from ApiHunt to internal Hunt model. */
export function translateHunt(hunt: ApiHunt): Hunt {
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
    created: createOptionalDate(hunt.created),
    creator: hunt.creator,
    description: hunt.description ?? '',
    duration: createOptionalDuration(hunt.duration),
    flowArgs: hunt.flowArgs,
    flowType: hunt.flowName ? translateApiFlowType(hunt.flowName) : undefined,
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
    state: translateHuntState(hunt.state, hunt.initStartTime),
    stateReason: hunt.stateReason ?? ApiHuntStateReason.UNKNOWN,
    stateComment: hunt.stateComment,
    resourceUsage: {
      totalCPUTime: hunt.totalCpuUsage ?? 0,
      totalNetworkTraffic: BigInt(hunt.totalNetUsage ?? 0),
    },
    safetyLimits: translateSafetyLimits(hunt.huntRunnerArgs),
    flowReference: hunt.originalObject?.flowReference,
    huntReference: hunt.originalObject?.huntReference,
    clientRuleSet: hunt.clientRuleSet,
    outputPlugins: (hunt.huntRunnerArgs.outputPlugins ?? []).map(
      translateOutputPlugin,
    ),
  };
}

/** Translates from ApiListHuntsResult to internal ListHuntsResult model. */
export function translateListHuntsResult(
  huntResult: ApiListHuntsResult,
): ListHuntsResult {
  return {
    hunts: huntResult.items?.map(translateHunt) ?? [],
    totalCount: huntResult.totalCount
      ? Number(huntResult.totalCount)
      : undefined,
  };
}

/** Translates from ApiHuntResult to internal HuntResult model. */
export function translateHuntResult(huntResult: ApiHuntResult): HuntResult {
  assertKeyNonNull(huntResult, 'clientId');
  assertKeyNonNull(huntResult, 'timestamp');

  return {
    clientId: huntResult.clientId,
    payload: createUnknownObject(huntResult.payload),
    payloadType:
      typeUrlToPayloadType(huntResult.payload?.['@type']) ?? undefined,
    timestamp: createDate(huntResult.timestamp),
  };
}

/** Translates from ApiHuntError to internal HuntError model. */
export function translateHuntError(huntError: ApiHuntError): HuntError {
  assertKeyNonNull(huntError, 'clientId');
  assertKeyNonNull(huntError, 'timestamp');

  return {
    clientId: huntError.clientId,
    logMessage: huntError.logMessage,
    backtrace: huntError.backtrace,
    timestamp: createDate(huntError.timestamp),
  };
}

/** Translates from internal ListHuntResultsArgs to ApiListHuntResultsArgs. */
export function toApiListHuntResultsArgs(
  args: ListHuntResultsArgs,
): ApiListHuntResultsArgs {
  return {
    huntId: args.huntId,
    count: args.count ? String(args.count) : undefined,
    offset: args.offset ? String(args.offset) : undefined,
    filter: args.filter ?? undefined,
    withType: args.withType ?? undefined,
  };
}

/** Translates from internal ListHuntErrorsArgs to ApiListHuntErrorsArgs. */
export function toApiListHuntErrorsArgs(
  args: ListHuntErrorsArgs,
): ApiListHuntErrorsArgs {
  return {
    huntId: args.huntId,
    count: args.count ? String(args.count) : undefined,
    offset: args.offset ? String(args.offset) : undefined,
    filter: args.filter ?? undefined,
  };
}

/**
 * Constructs a ListHuntResultsResult from the corresponding
 * ApiListHuntResultsResult.
 */
export function translateListHuntResultsResult(
  apiListHuntResultsResult: ApiListHuntResultsResult,
): ListHuntResultsResult {
  const totalCount = apiListHuntResultsResult.totalCount;
  return {
    totalCount: totalCount ? Number(totalCount) : undefined,
    results: apiListHuntResultsResult.items?.map(translateHuntResult) ?? [],
  };
}

/**
 * Constructs a ListHuntErrorsResult from the corresponding
 * ApiListHuntErrorsResult.
 */
export function translateListHuntErrorsResult(
  apiListHuntErrorsResult: ApiListHuntErrorsResult,
): ListHuntErrorsResult {
  const totalCount = apiListHuntErrorsResult.totalCount;
  return {
    totalCount: totalCount ? Number(totalCount) : undefined,
    errors: apiListHuntErrorsResult.items?.map(translateHuntError) ?? [],
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

/** Translates from ApiHuntLog to internal HuntLog model. */
export function translateHuntLog(huntLog: ApiHuntLog): HuntLog {
  return {
    clientId: huntLog.clientId,
    logMessage: huntLog.logMessage,
    flowName: huntLog.flowName,
    flowId: huntLog.flowId,
    timestamp: createOptionalDate(huntLog.timestamp),
  };
}

/** Translates from ApiListHuntLogsResult to internal ListHuntLogsResult model. */
export function translateListHuntLogsResult(
  apiListHuntLogsResult: ApiListHuntLogsResult,
): ListHuntLogsResult {
  const totalCount = apiListHuntLogsResult.totalCount;
  return {
    logs: apiListHuntLogsResult.items?.map(translateHuntLog) ?? [],
    totalCount: totalCount ? Number(totalCount) : undefined,
  };
}
