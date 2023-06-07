import {initTestEnvironment} from '../../testing';
import {ApiHuntState, HuntRunnerArgs} from '../api/api_interfaces';
import {HuntState, SafetyLimits} from '../models/hunt';

import {toApiHuntState, translateHuntState, translateSafetyLimits} from './hunt';

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

  it('converts to HuntState correctly', () => {
    expect(translateHuntState({
      state: ApiHuntState.PAUSED,
      initStartTime: '1234',
    })).toEqual(HuntState.REACHED_CLIENT_LIMIT);

    expect(translateHuntState({
      state: ApiHuntState.PAUSED,
      initStartTime: '',
    })).toEqual(HuntState.NOT_STARTED);
    expect(translateHuntState({
      state: ApiHuntState.PAUSED
    })).toEqual(HuntState.NOT_STARTED);

    expect(translateHuntState({
      state: ApiHuntState.STARTED
    })).toEqual(HuntState.RUNNING);

    expect(translateHuntState({
      state: ApiHuntState.STOPPED
    })).toEqual(HuntState.CANCELLED);

    expect(translateHuntState({
      state: ApiHuntState.COMPLETED
    })).toEqual(HuntState.REACHED_TIME_LIMIT);
  });

  it('converts to ApiHuntState correctly', () => {
    expect(toApiHuntState(HuntState.NOT_STARTED)).toEqual(ApiHuntState.PAUSED);
    expect(toApiHuntState(HuntState.REACHED_CLIENT_LIMIT))
        .toEqual(ApiHuntState.PAUSED);
    expect(toApiHuntState(HuntState.RUNNING)).toEqual(ApiHuntState.STARTED);
    expect(toApiHuntState(HuntState.CANCELLED)).toEqual(ApiHuntState.STOPPED);
    expect(toApiHuntState(HuntState.REACHED_TIME_LIMIT))
        .toEqual(ApiHuntState.COMPLETED);
  });
});
