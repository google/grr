import {HuntRunnerArgs} from '../api/api_interfaces';
import {SafetyLimits} from '../models/hunt';
import {assertNumber} from '../preconditions';

const TWO_WEEKS = 2 * 7 * 24 * 60 * 60;

/** Constructs a SafetyLimits from the HuntRunnerArgs */
export function translateSafetyLimits(args: HuntRunnerArgs): SafetyLimits {
  assertNumber(args.clientRate);

  return {
    clientRate: args.clientRate,
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
