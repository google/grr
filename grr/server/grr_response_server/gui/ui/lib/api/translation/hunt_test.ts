import {initTestEnvironment} from '../../../testing';
import {Duration} from '../../date_time';
import {FlowType} from '../../models/flow';
import {HuntState, HuntType, SafetyLimits} from '../../models/hunt';
import {PayloadType} from '../../models/result';
import {
  ApiHunt,
  ApiHuntError,
  ApiHuntHuntType,
  ApiHuntLog,
  ApiHuntResult,
  ApiHuntState,
  ApiHuntStateReason,
  ApiListHuntErrorsResult,
  ApiListHuntLogsResult,
  ApiListHuntResultsResult,
  ApiListHuntsArgsRobotFilter,
  ApiListHuntsResult,
  ForemanClientRuleSetMatchMode,
  HuntRunnerArgs,
} from '../api_interfaces';
import {newPathSpec} from '../api_test_util';
import {
  toApiHuntState,
  toApiListHuntErrorsArgs,
  toApiListHuntResultsArgs,
  toApiListHuntsArgs,
  translateHunt,
  translateHuntError,
  translateHuntLog,
  translateHuntResult,
  translateHuntState,
  translateListHuntErrorsResult,
  translateListHuntLogsResult,
  translateListHuntResultsResult,
  translateListHuntsResult,
  translateSafetyLimits,
} from './hunt';

initTestEnvironment();

describe('Hunt translation test', () => {
  describe('translateSafetyLimits', () => {
    it('converts HuntRunnerArgs correctly', () => {
      const huntRunnerArgs: HuntRunnerArgs = {
        clientRate: 200.0,
        clientLimit: '123',
        crashLimit: '100',
        avgResultsPerClientLimit: '1000',
        avgCpuSecondsPerClientLimit: '60',
        avgNetworkBytesPerClientLimit: '10485760',
        perClientCpuLimit: '123',
        perClientNetworkLimitBytes: '0',
        expiryTime: '123000',
      };

      const safetyLimits: SafetyLimits = {
        clientRate: 200.0,
        clientLimit: BigInt(123),
        crashLimit: BigInt(100),
        avgResultsPerClientLimit: BigInt(1000),
        avgCpuSecondsPerClientLimit: BigInt(60),
        avgNetworkBytesPerClientLimit: BigInt(10485760),
        perClientCpuLimit: BigInt(123),
        perClientNetworkBytesLimit: BigInt(0),
        expiryTime: BigInt(123000),
      };

      expect(translateSafetyLimits(huntRunnerArgs)).toEqual(safetyLimits);
    });
  });

  describe('translateHuntState', () => {
    it('converts to HuntState correctly', () => {
      expect(translateHuntState(ApiHuntState.PAUSED, '1234')).toEqual(
        HuntState.REACHED_CLIENT_LIMIT,
      );

      expect(translateHuntState(ApiHuntState.PAUSED, '')).toEqual(
        HuntState.NOT_STARTED,
      );
      expect(translateHuntState(ApiHuntState.PAUSED)).toEqual(
        HuntState.NOT_STARTED,
      );

      expect(translateHuntState(ApiHuntState.STARTED)).toEqual(
        HuntState.RUNNING,
      );

      expect(translateHuntState(ApiHuntState.STOPPED)).toEqual(
        HuntState.CANCELLED,
      );

      expect(translateHuntState(ApiHuntState.COMPLETED)).toEqual(
        HuntState.REACHED_TIME_LIMIT,
      );
    });
  });

  describe('toApiHuntState', () => {
    it('converts to ApiHuntState correctly', () => {
      expect(toApiHuntState(HuntState.NOT_STARTED)).toEqual(
        ApiHuntState.PAUSED,
      );
      expect(toApiHuntState(HuntState.RUNNING)).toEqual(ApiHuntState.STARTED);
      expect(toApiHuntState(HuntState.CANCELLED)).toEqual(ApiHuntState.STOPPED);
      expect(toApiHuntState(HuntState.REACHED_TIME_LIMIT)).toEqual(
        ApiHuntState.COMPLETED,
      );
      expect(toApiHuntState(HuntState.REACHED_CLIENT_LIMIT)).toEqual(
        ApiHuntState.PAUSED,
      );
    });
  });

  describe('toApiListHuntsArgs', () => {
    it('converts all fields correctly to ApiListHuntsArgs', () => {
      expect(
        toApiListHuntsArgs({
          count: 10,
          offset: 3,
          robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
          stateFilter: HuntState.NOT_STARTED,
        }),
      ).toEqual({
        count: '10',
        offset: '3',
        robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
        withState: ApiHuntState.PAUSED,
      });
    });

    it('converts only required fields correctly to ApiListHuntsArgs', () => {
      expect(toApiListHuntsArgs({})).toEqual({
        count: undefined,
        offset: undefined,
        robotFilter: undefined,
        withState: undefined,
      });
    });
  });

  describe('translateHunt', () => {
    it('converts all fields correctly to Hunt', () => {
      const apiHunt: ApiHunt = {
        urn: 'session-id',
        huntId: 'hunt-id',
        huntType: ApiHuntHuntType.STANDARD,
        name: 'hunt-name',
        state: ApiHuntState.PAUSED,
        stateReason: ApiHuntStateReason.DEADLINE_REACHED,
        stateComment: 'state-comment',
        flowName: 'ArtifactCollectorFlow',
        flowArgs: {},
        huntRunnerArgs: {
          clientRate: 12,
        },
        allClientsCount: '123',
        remainingClientsCount: '456',
        completedClientsCount: '789',
        failedClientsCount: '101112',
        crashedClientsCount: '131415',
        crashLimit: '161718',
        clientRate: 12,
        created: '111111000',
        initStartTime: '222222000',
        lastStartTime: '333333000',
        deprecatedExpires: '444444000',
        duration: '1',
        creator: 'creator',
        description: 'description',
        clientRuleSet: {
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [],
        },
        isRobot: true,
        totalCpuUsage: 123.4,
        totalNetUsage: '1234',
        clientsWithResultsCount: '2345',
        resultsCount: '3456',
        originalObject: {
          flowReference: {
            flowId: 'flow-id',
            clientId: 'client-id',
          },
          huntReference: {
            huntId: 'hunt-id',
          },
        },
        internalError: 'internal-error',
      };
      expect(translateHunt(apiHunt)).toEqual({
        allClientsCount: BigInt(123),
        clientsWithResultsCount: BigInt(2345),
        completedClientsCount: BigInt(789),
        crashedClientsCount: BigInt(131415),
        failedClientsCount: BigInt(101112),
        created: new Date(111111),
        creator: 'creator',
        description: 'description',
        duration: Duration.fromObject({seconds: 1}),
        flowArgs: {},
        flowName: 'ArtifactCollectorFlow',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        huntId: 'hunt-id',
        huntType: HuntType.STANDARD,
        initStartTime: new Date(222222),
        internalError: 'internal-error',
        isRobot: true,
        lastStartTime: new Date(333333),
        name: 'hunt-name',
        remainingClientsCount: BigInt(456),
        resultsCount: BigInt(3456),
        state: HuntState.REACHED_CLIENT_LIMIT,
        stateReason: ApiHuntStateReason.DEADLINE_REACHED,
        stateComment: 'state-comment',
        safetyLimits: {
          clientRate: 12,
          clientLimit: BigInt(0),
          crashLimit: BigInt(0),
          avgResultsPerClientLimit: BigInt(0),
          avgCpuSecondsPerClientLimit: BigInt(0),
          avgNetworkBytesPerClientLimit: BigInt(0),
          perClientCpuLimit: BigInt(0),
          perClientNetworkBytesLimit: BigInt(0),
          expiryTime: BigInt(2 * 7 * 24 * 60 * 60), // 2 weeks
        },
        flowReference: {
          flowId: 'flow-id',
          clientId: 'client-id',
        },
        huntReference: {
          huntId: 'hunt-id',
        },
        clientRuleSet: {
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [],
        },
        outputPlugins: [],
        resourceUsage: {
          totalCPUTime: 123.4,
          totalNetworkTraffic: BigInt(1234),
        },
      });
    });

    it('converts optional fields correctly to Hunt', () => {
      const apiHunt: ApiHunt = {
        created: '0',
        creator: '',
        name: '',
        state: ApiHuntState.STARTED,
        huntId: '',
        huntRunnerArgs: {
          clientRate: 0,
        },
      };
      expect(translateHunt(apiHunt)).toEqual({
        allClientsCount: BigInt(0),
        clientsWithResultsCount: BigInt(0),
        completedClientsCount: BigInt(0),
        crashedClientsCount: BigInt(0),
        failedClientsCount: BigInt(0),
        created: new Date(0),
        creator: '',
        description: '',
        duration: undefined,
        flowArgs: undefined,
        flowName: undefined,
        flowType: undefined,
        huntId: '',
        huntType: HuntType.UNSET,
        initStartTime: undefined,
        internalError: undefined,
        isRobot: false,
        lastStartTime: undefined,
        name: '',
        remainingClientsCount: BigInt(0),
        resultsCount: BigInt(0),
        state: HuntState.RUNNING,
        stateReason: ApiHuntStateReason.UNKNOWN,
        stateComment: undefined,
        safetyLimits: {
          clientRate: 0,
          clientLimit: BigInt(0),
          crashLimit: BigInt(0),
          avgResultsPerClientLimit: BigInt(0),
          avgCpuSecondsPerClientLimit: BigInt(0),
          avgNetworkBytesPerClientLimit: BigInt(0),
          perClientCpuLimit: BigInt(0),
          perClientNetworkBytesLimit: BigInt(0),
          expiryTime: BigInt(2 * 7 * 24 * 60 * 60), // 2 weeks
        },
        flowReference: undefined,
        huntReference: undefined,
        clientRuleSet: undefined,
        outputPlugins: [],
        resourceUsage: {
          totalCPUTime: 0,
          totalNetworkTraffic: BigInt(0),
        },
      });
    });
  });

  describe('translateHuntResult', () => {
    it('converts all fields correctly to HuntResult', () => {
      const apiHuntResult: ApiHuntResult = {
        clientId: 'C.1234567890',
        timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
        payload: {
          '@type': 'example.com/grr.StatEntry',
          'path': newPathSpec('/foo/bar'),
        },
      };
      expect(translateHuntResult(apiHuntResult)).toEqual({
        clientId: 'C.1234567890',
        timestamp: new Date(1571789996681),
        payload: {
          'path': newPathSpec('/foo/bar'),
        },
        payloadType: PayloadType.STAT_ENTRY,
      });
    });

    it('converts optional fields correctly to HuntResult', () => {
      const apiHuntResult: ApiHuntResult = {
        clientId: 'C.1234567890',
        timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
      };
      expect(translateHuntResult(apiHuntResult)).toEqual({
        clientId: 'C.1234567890',
        payload: undefined,
        payloadType: undefined,
        timestamp: new Date(1571789996681),
      });
    });
  });

  describe('translateHuntError', () => {
    it('converts all fields correctly to HuntResult', () => {
      const apiHuntError: ApiHuntError = {
        clientId: 'C.1234567890',
        timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
        logMessage: 'log-message',
        backtrace: 'backtrace',
      };
      expect(translateHuntError(apiHuntError)).toEqual({
        clientId: 'C.1234567890',
        timestamp: new Date(1571789996681),
        logMessage: 'log-message',
        backtrace: 'backtrace',
      });
    });

    it('converts optional fields correctly to HuntError', () => {
      const apiHuntError: ApiHuntError = {
        clientId: 'C.1234567890',
        timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
      };
      expect(translateHuntError(apiHuntError)).toEqual({
        clientId: 'C.1234567890',
        timestamp: new Date(1571789996681),
        logMessage: undefined,
        backtrace: undefined,
      });
    });
  });

  describe('translateListHuntResultsResult', () => {
    it('converts all fields correctly to ListHuntResultsResult', () => {
      const apiListHuntResultsResult: ApiListHuntResultsResult = {
        totalCount: '10',
        items: [
          {
            clientId: 'C.1234567890',
            timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
            payload: {
              '@type': 'example.com/grr.StatEntry',
              'path': newPathSpec('/foo/bar'),
            },
          },
        ],
      };
      expect(translateListHuntResultsResult(apiListHuntResultsResult)).toEqual({
        totalCount: 10,
        results: [
          {
            clientId: 'C.1234567890',
            timestamp: new Date(1571789996681),
            payload: {
              'path': newPathSpec('/foo/bar'),
            },
            payloadType: PayloadType.STAT_ENTRY,
          },
        ],
      });
    });

    it('converts optional fields correctly to ListHuntResultsResult', () => {
      const apiListHuntResultsResult: ApiListHuntResultsResult = {
        items: [
          {
            clientId: 'C.1234567890',
            timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
          },
        ],
      };
      expect(translateListHuntResultsResult(apiListHuntResultsResult)).toEqual({
        totalCount: undefined,
        results: [
          {
            clientId: 'C.1234567890',
            timestamp: new Date(1571789996681),
            payload: undefined,
            payloadType: undefined,
          },
        ],
      });
    });
  });

  describe('translateListHuntErrorsResult', () => {
    it('converts all fields correctly to ListHuntErrorsResult', () => {
      const apiListHuntErrorsResult: ApiListHuntErrorsResult = {
        totalCount: '10',
        items: [
          {
            clientId: 'C.1234567890',
            timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
            logMessage: 'log-message',
            backtrace: 'backtrace',
          },
        ],
      };
      expect(translateListHuntErrorsResult(apiListHuntErrorsResult)).toEqual({
        totalCount: 10,
        errors: [
          {
            clientId: 'C.1234567890',
            timestamp: new Date(1571789996681),
            logMessage: 'log-message',
            backtrace: 'backtrace',
          },
        ],
      });
    });

    it('converts optional fields correctly to ListHuntErrorsResult', () => {
      const apiListHuntErrorsResult: ApiListHuntErrorsResult = {
        items: [
          {
            clientId: 'C.1234567890',
            timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
          },
        ],
      };
      expect(translateListHuntErrorsResult(apiListHuntErrorsResult)).toEqual({
        totalCount: undefined,
        errors: [
          {
            clientId: 'C.1234567890',
            timestamp: new Date(1571789996681),
            logMessage: undefined,
            backtrace: undefined,
          },
        ],
      });
    });
  });

  describe('toApiListHuntResultsArgs', () => {
    it('converts all fields correctly to ApiListHuntResultsArgs', () => {
      expect(
        toApiListHuntResultsArgs({
          huntId: 'hunt-id',
          offset: 10,
          count: 20,
          filter: 'filter',
          withType: 'with-type',
        }),
      ).toEqual({
        huntId: 'hunt-id',
        offset: '10',
        count: '20',
        filter: 'filter',
        withType: 'with-type',
      });
    });

    it('converts only required fields correctly to ApiListHuntResultsArgs', () => {
      expect(toApiListHuntResultsArgs({huntId: 'hunt-id'})).toEqual({
        huntId: 'hunt-id',
        offset: undefined,
        count: undefined,
        filter: undefined,
        withType: undefined,
      });
    });
  });

  describe('toApiListHuntErrorsArgs', () => {
    it('converts all fields correctly to ApiListHuntErrorsArgs', () => {
      expect(
        toApiListHuntErrorsArgs({
          huntId: 'hunt-id',
          offset: 10,
          count: 20,
          filter: 'filter',
        }),
      ).toEqual({
        huntId: 'hunt-id',
        offset: '10',
        count: '20',
        filter: 'filter',
      });
    });

    it('converts only required fields correctly to ApiListHuntErrorsArgs', () => {
      expect(toApiListHuntErrorsArgs({huntId: 'hunt-id'})).toEqual({
        huntId: 'hunt-id',
        offset: undefined,
        count: undefined,
        filter: undefined,
      });
    });
  });

  describe('translateListHuntsResult', () => {
    it('converts all fields correctly to ListHuntsResult', () => {
      const apiListHuntsResult: ApiListHuntsResult = {
        items: [
          {
            created: '0',
            creator: '',
            name: '',
            state: ApiHuntState.STARTED,
            huntId: '',
            huntRunnerArgs: {
              clientRate: 0,
            },
          },
        ],
        totalCount: '1',
      };

      expect(translateListHuntsResult(apiListHuntsResult)).toEqual({
        hunts: [
          {
            allClientsCount: BigInt(0),
            clientsWithResultsCount: BigInt(0),
            completedClientsCount: BigInt(0),
            crashedClientsCount: BigInt(0),
            failedClientsCount: BigInt(0),
            created: new Date(0),
            creator: '',
            description: '',
            duration: undefined,
            flowArgs: undefined,
            flowName: undefined,
            flowType: undefined,
            huntId: '',
            huntType: HuntType.UNSET,
            initStartTime: undefined,
            internalError: undefined,
            isRobot: false,
            lastStartTime: undefined,
            name: '',
            remainingClientsCount: BigInt(0),
            resultsCount: BigInt(0),
            state: HuntState.RUNNING,
            stateReason: ApiHuntStateReason.UNKNOWN,
            stateComment: undefined,
            safetyLimits: {
              clientRate: 0,
              clientLimit: BigInt(0),
              crashLimit: BigInt(0),
              avgResultsPerClientLimit: BigInt(0),
              avgCpuSecondsPerClientLimit: BigInt(0),
              avgNetworkBytesPerClientLimit: BigInt(0),
              perClientCpuLimit: BigInt(0),
              perClientNetworkBytesLimit: BigInt(0),
              expiryTime: BigInt(2 * 7 * 24 * 60 * 60), // 2 weeks
            },
            flowReference: undefined,
            huntReference: undefined,
            clientRuleSet: undefined,
            outputPlugins: [],
            resourceUsage: {
              totalCPUTime: 0,
              totalNetworkTraffic: BigInt(0),
            },
          },
        ],
        totalCount: 1,
      });
    });
  });

  describe('translateHuntLog', () => {
    it('converts all fields correctly to HuntLog', () => {
      const apiHuntLog: ApiHuntLog = {
        clientId: 'C.1234567890',
        logMessage: 'log-message',
        flowName: 'flow-name',
        flowId: 'flow-id',
        timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
      };
      expect(translateHuntLog(apiHuntLog)).toEqual({
        clientId: 'C.1234567890',
        logMessage: 'log-message',
        flowName: 'flow-name',
        flowId: 'flow-id',
        timestamp: new Date(1571789996681),
      });
    });

    it('converts optional fields correctly to HuntLog', () => {
      const apiHuntLog: ApiHuntLog = {};
      expect(translateHuntLog(apiHuntLog)).toEqual({
        clientId: undefined,
        logMessage: undefined,
        flowName: undefined,
        flowId: undefined,
        timestamp: undefined,
      });
    });
  });

  describe('translateListHuntLogsResult', () => {
    it('converts all fields correctly to ListHuntLogsResult', () => {
      const apiListHuntLogsResult: ApiListHuntLogsResult = {
        totalCount: '10',
        items: [
          {
            clientId: 'C.1234567890',
            logMessage: 'log-message',
            flowName: 'flow-name',
            flowId: 'flow-id',
            timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
          },
        ],
      };
      expect(translateListHuntLogsResult(apiListHuntLogsResult)).toEqual({
        totalCount: 10,
        logs: [
          {
            clientId: 'C.1234567890',
            logMessage: 'log-message',
            flowName: 'flow-name',
            flowId: 'flow-id',
            timestamp: new Date(1571789996681),
          },
        ],
      });
    });
  });
});
