import {initTestEnvironment} from '../../testing';
import {HuntRunnerArgs} from '../api/api_interfaces';
import {SafetyLimits} from '../models/hunt';

import {translateSafetyLimits} from './hunt';

initTestEnvironment();

describe('Hunt translation test', () => {
  it('converts HuntRunnerArgs correctly', () => {
    const huntRunnerArgs: HuntRunnerArgs = {
      clientRate: 200.0,
      clientLimit: '123',
      crashLimit: '100',
      avgResultsPerClientLimit: '1000',
      avgCpuSecondsPerClientLimit: '60',
      avgNetworkBytesPerClientLimit: '10485760',
      cpuLimit: '123',
      expiryTime: '123000',
      networkBytesLimit: '0'
    };

    const safetyLimits: SafetyLimits = {
      clientRate: 200.0,
      clientLimit: BigInt(123),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
      cpuLimit: BigInt(123),
      expiryTime: BigInt(123000),
      networkBytesLimit: BigInt(0),
    };

    expect(translateSafetyLimits(huntRunnerArgs)).toEqual(safetyLimits);
  });
});
