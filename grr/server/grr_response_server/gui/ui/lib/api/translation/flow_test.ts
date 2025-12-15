import {initTestEnvironment} from '../../../testing';
import {
  Binary,
  BinaryType,
  CollectLargeFileFlowResult,
  ContainerCli,
  ContainerDetails,
  ContainerLabel,
  ContainerState,
  ExecuteBinaryResponse,
  Flow,
  FlowLog,
  FlowLogs,
  FlowResult,
  FlowState,
  FlowType,
  GetMemorySizeResult,
  ListFlowResultsResult,
  OutputPluginLogEntryType,
  RegistryType,
  SoftwarePackage,
  SoftwarePackageInstallState,
} from '../../models/flow';
import {StatEntry} from '../../models/vfs';
import {PreconditionError} from '../../preconditions';
import {
  CollectLargeFileFlowResult as ApiCollectLargeFileFlowResult,
  ContainerDetails as ApiContainerDetails,
  ContainerDetailsContainerCli as ApiContainerDetailsContainerCli,
  ContainerDetailsContainerState as ApiContainerDetailsContainerState,
  ContainerLabel as ApiContainerLabel,
  ExecuteBinaryResponse as ApiExecuteBinaryResponse,
  ApiFlow,
  ApiFlowLog,
  ApiFlowResult,
  ApiFlowState,
  GetMemorySizeResult as ApiGetMemorySizeResult,
  ApiGrrBinary,
  ApiGrrBinaryType,
  ApiListAllFlowOutputPluginLogsResult,
  ApiListFlowLogsResult,
  ApiListFlowResultsResult,
  StatEntryRegistryType as ApiRegistryType,
  ApiScheduledFlow,
  SoftwarePackage as ApiSoftwarePackage,
  SoftwarePackageInstallState as ApiSoftwarePackageInstallState,
  StatEntry as ApiStatEntry,
  FlowOutputPluginLogEntry,
  FlowOutputPluginLogEntryLogEntryType,
  PathSpecPathType,
} from '../api_interfaces';
import {newPathSpec} from '../api_test_util';

import {PayloadType} from '../../models/result';
import {
  isRegistryValue,
  safeTranslateBinary,
  translateApiFlowType,
  translateBinary,
  translateCollectLargeFileFlowResult,
  translateContainerCli,
  translateContainerDetails,
  translateContainerLabel,
  translateContainerState,
  translateExecuteBinaryResponse,
  translateFlow,
  translateFlowLog,
  translateFlowLogs,
  translateFlowResult,
  translateGetMemorySizeResult,
  translateHashToHex,
  translateListAllOutputPluginLogsResult,
  translateListFlowResultsResult,
  translateOutputPluginLog,
  translateOutputPluginLogEntryType,
  translateScheduledFlow,
  translateSoftwarePackage,
  translateSoftwarePackageInstallState,
  translateStatEntry,
  translateVfsStatEntry,
} from './flow';

initTestEnvironment();

describe('Flow API Translation', () => {
  it('converts populated ApiFlow correctly', () => {
    const apiFlow: ApiFlow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'Kill',
      creator: 'morty',
      lastActiveAt: '1111111111111000',
      startedAt: '1222222222222000',
      state: ApiFlowState.TERMINATED,
      isRobot: false,
      args: {
        '@type': 'example.com/grr.Args',
        'value': '/foo/bar',
      },
      nestedFlows: [
        {
          flowId: '5678',
          clientId: 'C.4567',
          name: 'OnlineNotification',
          creator: 'morty',
          lastActiveAt: '1333333333333000',
          startedAt: '1444444444444000',
          state: ApiFlowState.TERMINATED,
          isRobot: false,
          nestedFlows: [
            {
              flowId: '9012',
              clientId: 'C.4567',
              name: 'Kill',
              creator: 'morty',
              lastActiveAt: '1555555555555000',
              startedAt: '1666666666666000',
              state: ApiFlowState.TERMINATED,
              isRobot: false,
            },
          ],
        },
      ],
      context: {
        backtrace: 'Stacktrace',
        status: 'Running',
      },
      store: {
        '@type': 'foo',
        'bar': 'baz',
      },
    };

    const flow: Flow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'Kill',
      flowType: FlowType.KILL,
      creator: 'morty',
      lastActiveAt: new Date(1111111111111),
      startedAt: new Date(1222222222222),
      args: {'value': '/foo/bar'},
      progress: undefined,
      state: FlowState.FINISHED,
      errorDescription: undefined,
      resultCounts: undefined,
      isRobot: false,
      nestedFlows: [
        {
          flowId: '5678',
          clientId: 'C.4567',
          name: 'OnlineNotification',
          flowType: FlowType.ONLINE_NOTIFICATION,
          creator: 'morty',
          lastActiveAt: new Date(1333333333333),
          startedAt: new Date(1444444444444),
          args: undefined,
          progress: undefined,
          state: FlowState.FINISHED,
          errorDescription: undefined,
          resultCounts: undefined,
          isRobot: false,
          nestedFlows: [
            {
              flowId: '9012',
              clientId: 'C.4567',
              name: 'Kill',
              flowType: FlowType.KILL,
              creator: 'morty',
              lastActiveAt: new Date(1555555555555),
              startedAt: new Date(1666666666666),
              args: undefined,
              progress: undefined,
              state: FlowState.FINISHED,
              errorDescription: undefined,
              resultCounts: undefined,
              isRobot: false,
              nestedFlows: undefined,
              context: undefined,
              store: undefined,
            },
          ],
          context: undefined,
          store: undefined,
        },
      ],
      context: {
        backtrace: 'Stacktrace',
        status: 'Running',
      },
      store: {
        '@type': 'foo',
        'bar': 'baz',
      },
    };

    expect(translateFlow(apiFlow)).toEqual(flow);
  });

  it('converts CLIENT_TERMINATED status to ERROR', () => {
    const apiFlow: ApiFlow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'Kill',
      creator: 'morty',
      lastActiveAt: '1571789996681000', // 2019-10-23T00:19:56.681Z
      startedAt: '1571789996679000', // 2019-10-23T00:19:56.679Z
      state: ApiFlowState.CLIENT_CRASHED,
      isRobot: false,
    };

    expect(translateFlow(apiFlow)).toEqual(
      jasmine.objectContaining({
        state: FlowState.ERROR,
      }),
    );
  });
});

describe('translateOutputPluginLogEntryType', () => {
  it('converts all fields correctly', () => {
    expect(
      translateOutputPluginLogEntryType(
        FlowOutputPluginLogEntryLogEntryType.UNSET,
      ),
    ).toEqual(OutputPluginLogEntryType.UNSET);
    expect(
      translateOutputPluginLogEntryType(
        FlowOutputPluginLogEntryLogEntryType.ERROR,
      ),
    ).toEqual(OutputPluginLogEntryType.ERROR);
    expect(
      translateOutputPluginLogEntryType(
        FlowOutputPluginLogEntryLogEntryType.LOG,
      ),
    ).toEqual(OutputPluginLogEntryType.LOG);
  });
});

describe('translateOutputPluginLog', () => {
  it('converts all fields correctly', () => {
    const apiOutputPluginLogEntry: FlowOutputPluginLogEntry = {
      flowId: 'flowId',
      clientId: 'clientId',
      huntId: 'huntId',
      outputPluginId: 'outputPluginId',
      logEntryType: FlowOutputPluginLogEntryLogEntryType.ERROR,
      timestamp: '123456789000',
      message: 'message',
    };
    expect(translateOutputPluginLog(apiOutputPluginLogEntry)).toEqual({
      flowId: 'flowId',
      clientId: 'clientId',
      huntId: 'huntId',
      outputPluginId: 'outputPluginId',
      logEntryType: OutputPluginLogEntryType.ERROR,
      timestamp: new Date(123456789),
      message: 'message',
    });
  });
});

describe('translateListAllOutputPluginLogsResult', () => {
  it('converts all fields correctly', () => {
    const apiListAllOutputPluginLogsResult: ApiListAllFlowOutputPluginLogsResult =
      {
        items: [
          {
            flowId: 'flowId',
            clientId: 'clientId',
            huntId: 'huntId',
            outputPluginId: 'outputPluginId',
            logEntryType: FlowOutputPluginLogEntryLogEntryType.ERROR,
            timestamp: '123456789000',
            message: 'message',
          },
        ],
        totalCount: '1',
      };
    expect(
      translateListAllOutputPluginLogsResult(apiListAllOutputPluginLogsResult),
    ).toEqual({
      items: [
        {
          flowId: 'flowId',
          clientId: 'clientId',
          huntId: 'huntId',
          outputPluginId: 'outputPluginId',
          logEntryType: OutputPluginLogEntryType.ERROR,
          timestamp: new Date(123456789),
          message: 'message',
        },
      ],
      totalCount: 1,
    });
  });
});

describe('translateApiFlowType', () => {
  it('returns undefined for unknown flow type', () => {
    expect(translateApiFlowType('UnknownFlow')).toBeUndefined();
  });

  it('returns flow type for known flow type', () => {
    expect(translateApiFlowType('Kill')).toBe(FlowType.KILL);
  });
});

describe('translateScheduledFlow', () => {
  it('converts ApiScheduledFlow to ScheduledFlow correctly', () => {
    const apiScheduledFlow: ApiScheduledFlow = {
      scheduledFlowId: '1234',
      clientId: 'C.4567',
      creator: 'morty',
      flowName: 'Kill',
      flowArgs: {
        '@type': 'example.com/grr.Args',
        'value': '/foo/bar',
      },
      createTime: '1111111111111000',
      error: 'error',
    };

    expect(translateScheduledFlow(apiScheduledFlow)).toEqual({
      scheduledFlowId: '1234',
      clientId: 'C.4567',
      creator: 'morty',
      flowName: 'Kill',
      flowType: FlowType.KILL,
      flowArgs: {'value': '/foo/bar'},
      createTime: new Date(1111111111111),
      error: 'error',
    });
  });
});

describe('translateExecuteBinaryResponse', () => {
  it('converts complete ApiExecuteBinaryResponse to ExecuteBinaryResponse correctly', () => {
    const apiExecuteBinaryResponse: ApiExecuteBinaryResponse = {
      stdout: btoa('stdout\nline two'),
      stderr: btoa('stderr'),
      exitStatus: 1,
      timeUsed: 1e6,
    };

    const executeBinaryResponse: ExecuteBinaryResponse = {
      stdout: ['stdout', 'line two'],
      stderr: ['stderr'],
      exitStatus: 1,
      timeUsedSeconds: 1,
    };

    expect(translateExecuteBinaryResponse(apiExecuteBinaryResponse)).toEqual(
      executeBinaryResponse,
    );
  });

  it('converts empty ApiExecuteBinaryResponse to ExecuteBinaryResponse correctly', () => {
    const apiExecuteBinaryResponse: ApiExecuteBinaryResponse = {};

    const executeBinaryResponse: ExecuteBinaryResponse = {
      stdout: [],
      stderr: [],
      exitStatus: -1,
      timeUsedSeconds: 0,
    };

    expect(translateExecuteBinaryResponse(apiExecuteBinaryResponse)).toEqual(
      executeBinaryResponse,
    );
  });
});

describe('translateFlowLog', () => {
  it('converts complete ApiFlowLog correctly to FlowLog', () => {
    const apiFlowLog: ApiFlowLog = {
      timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
      logMessage: 'log message',
    };
    const flowLog: FlowLog = {
      timestamp: new Date(1571789996681),
      logMessage: 'log message',
    };

    expect(translateFlowLog(apiFlowLog)).toEqual(flowLog);
  });

  it('converts ApiFlowLog without optional fields correctly to FlowLog', () => {
    const apiFlowLog: ApiFlowLog = {
      timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
    };
    const flowLog: FlowLog = {
      timestamp: new Date(1571789996681),
      logMessage: undefined,
    };

    expect(translateFlowLog(apiFlowLog)).toEqual(flowLog);
  });
});

describe('translateFlowLogs', () => {
  it('converts complete ApiFlowLogs correctly to FlowLogs ', () => {
    const apiFlowLogs: ApiListFlowLogsResult = {
      items: [],
      totalCount: '2',
    };
    const flowLogs: FlowLogs = {
      items: [],
      totalCount: 2,
    };

    expect(translateFlowLogs(apiFlowLogs)).toEqual(flowLogs);
  });

  it('converts ApiFlowLogs without optional fields correctly to FlowLogs', () => {
    const apiFlowLogs: ApiListFlowLogsResult = {};
    const flowLogs: FlowLogs = {
      items: [],
      totalCount: undefined,
    };

    expect(translateFlowLogs(apiFlowLogs)).toEqual(flowLogs);
  });
});

describe('translateFlowResult', () => {
  it('converts ApiFlowResult to FlowResult correctly', () => {
    const apiFlowResult: ApiFlowResult = {
      payload: {
        '@type': 'example.com/grr.StatEntry',
        'path': newPathSpec('/foo/bar'),
      },
      timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
      tag: 'someTag',
    };

    const flowResult: FlowResult = {
      clientId: 'C.1234',
      payload: {
        'path': newPathSpec('/foo/bar'),
      },
      payloadType: PayloadType.STAT_ENTRY,
      tag: 'someTag',
      timestamp: new Date(1571789996681),
    };

    expect(translateFlowResult('C.1234', apiFlowResult)).toEqual(flowResult);
  });
});

describe('translateListFlowResultsResult', () => {
  it('converts ApiListFlowResultsResult to ListFlowResultsResult correctly', () => {
    const apiListFlowResultsResult: ApiListFlowResultsResult = {
      totalCount: '10',
      items: [
        {
          payload: {
            '@type': 'example.com/grr.StatEntry',
            'path': newPathSpec('/foo/bar'),
          },
          timestamp: '1571789996681000', // 2019-10-23T00:19:56.681Z
          tag: 'someTag',
        },
      ],
    };

    const listFlowResultsResult: ListFlowResultsResult = {
      totalCount: 10,
      results: [
        {
          clientId: 'C.1234',
          payload: {
            'path': newPathSpec('/foo/bar'),
          },
          payloadType: PayloadType.STAT_ENTRY,
          tag: 'someTag',
          timestamp: new Date(1571789996681),
        },
      ],
    };
    expect(
      translateListFlowResultsResult('C.1234', apiListFlowResultsResult),
    ).toEqual(listFlowResultsResult);
  });
});

function encodeBase64(bytes: number[]): string {
  return btoa(bytes.map((b) => String.fromCharCode(b)).join(''));
}

describe('translateHashToHex', () => {
  it('translates an empty object to an empty object', () => {
    expect(translateHashToHex({})).toEqual(jasmine.objectContaining({}));
  });

  it('converts base64-encoded bytes to hex', () => {
    const base64 = '0h4jIWBHN0HOLBVJnSZhJg==';
    expect(translateHashToHex({md5: base64})).toEqual(
      jasmine.objectContaining({
        md5: 'd21e232160473741ce2c15499d266126',
      }),
    );
  });

  it('converts sha1, sha256, and md5', () => {
    expect(
      translateHashToHex({
        md5: encodeBase64([0x12]),
        sha1: encodeBase64([0x34]),
        sha256: encodeBase64([0x56]),
      }),
    ).toEqual({
      md5: '12',
      sha1: '34',
      sha256: '56',
    });
  });
});

describe('translateVfsStatEntry', () => {
  it('returns a StatEntry as fallback', () => {
    expect(
      translateVfsStatEntry({
        pathspec: {path: 'foo', pathtype: 'OS' as PathSpecPathType},
      }),
    ).toEqual({
      stMode: undefined,
      stIno: undefined,
      stDev: undefined,
      stNlink: undefined,
      stUid: undefined,
      stGid: undefined,
      stSize: undefined,
      stAtime: undefined,
      stMtime: undefined,
      stCtime: undefined,
      stBtime: undefined,
      stBlocks: undefined,
      stBlksize: undefined,
      stRdev: undefined,
      stFlagsOsx: undefined,
      stFlagsLinux: undefined,
      symlink: undefined,
      pathspec: {
        path: 'foo',
        pathtype: PathSpecPathType.OS,
        segments: [{path: 'foo', pathtype: PathSpecPathType.OS}],
      },
    });
  });

  it('returns a RegistryValue if registryType is set', () => {
    expect(
      translateVfsStatEntry({
        pathspec: {path: 'foo', pathtype: PathSpecPathType.REGISTRY},
        registryType: ApiRegistryType.REG_NONE,
        registryData: {
          string: 'foo',
        },
      }),
    ).toEqual({
      path: 'foo',
      type: RegistryType.REG_NONE,
      value: {
        string: 'foo',
      },
    });
  });

  it('returns a RegistryKey for non-Registry-Values with PathType REGISTRY', () => {
    expect(
      translateVfsStatEntry({
        pathspec: {path: 'foo', pathtype: PathSpecPathType.REGISTRY},
      }),
    ).toEqual({
      path: 'foo',
      type: 'REG_KEY',
    });
  });
});

describe('translateCollectLargeFileFlowResult', () => {
  it('converts all fields correctly', () => {
    const result: ApiCollectLargeFileFlowResult = {
      sessionUri: 'session-uri',
      totalBytesSent: '100',
    };
    const expectedResult: CollectLargeFileFlowResult = {
      sessionUri: 'session-uri',
      totalBytesSent: BigInt(100),
    };
    expect(translateCollectLargeFileFlowResult(result)).toEqual(expectedResult);
  });

  it('converts optional fields correctly', () => {
    const result: ApiCollectLargeFileFlowResult = {};
    const expectedResult: CollectLargeFileFlowResult = {
      sessionUri: '',
      totalBytesSent: undefined,
    };
    expect(translateCollectLargeFileFlowResult(result)).toEqual(expectedResult);
  });
});

describe('translateContainerLabel', () => {
  it('converts all fields correctly', () => {
    const result: ApiContainerLabel = {
      label: 'label',
      value: 'value',
    };
    const expectedResult: ContainerLabel = {
      key: 'label',
      value: 'value',
    };
    expect(translateContainerLabel(result)).toEqual(expectedResult);
  });
});

describe('translateContainerState', () => {
  it('converts all fields correctly', () => {
    expect(
      translateContainerState(
        ApiContainerDetailsContainerState.CONTAINER_UNKNOWN,
      ),
    ).toEqual(ContainerState.UNKNOWN);
    expect(
      translateContainerState(
        ApiContainerDetailsContainerState.CONTAINER_CREATED,
      ),
    ).toEqual(ContainerState.CREATED);
    expect(
      translateContainerState(
        ApiContainerDetailsContainerState.CONTAINER_RUNNING,
      ),
    ).toEqual(ContainerState.RUNNING);
    expect(
      translateContainerState(
        ApiContainerDetailsContainerState.CONTAINER_PAUSED,
      ),
    ).toEqual(ContainerState.PAUSED);
    expect(
      translateContainerState(
        ApiContainerDetailsContainerState.CONTAINER_EXITED,
      ),
    ).toEqual(ContainerState.EXITED);
  });
});

describe('translateContainerCli', () => {
  it('converts all fields correctly', () => {
    expect(
      translateContainerCli(ApiContainerDetailsContainerCli.UNSUPPORTED),
    ).toEqual(ContainerCli.UNSUPPORTED);
    expect(
      translateContainerCli(ApiContainerDetailsContainerCli.CRICTL),
    ).toEqual(ContainerCli.CRICTL);
    expect(
      translateContainerCli(ApiContainerDetailsContainerCli.DOCKER),
    ).toEqual(ContainerCli.DOCKER);
  });
});

describe('translateContainerDetails', () => {
  it('converts all fields correctly', () => {
    const result: ApiContainerDetails = {
      containerId: 'container-id',
      imageName: 'image-name',
      command: 'command',
      createdAt: '888000',
      status: 'status',
      ports: ['port1', 'port2'],
      names: ['name1', 'name2'],
      labels: [
        {label: 'label1', value: 'value1'},
        {label: 'label2', value: 'value2'},
      ],
      localVolumes: 'local-volumes',
      mounts: ['mount1', 'mount2'],
      networks: ['network1', 'network2'],
      runningSince: '999000',
      state: ApiContainerDetailsContainerState.CONTAINER_RUNNING,
      containerCli: ApiContainerDetailsContainerCli.CRICTL,
    };
    const expectedResult: ContainerDetails = {
      containerId: 'container-id',
      imageName: 'image-name',
      command: 'command',
      createdAt: new Date(888),
      status: 'status',
      ports: ['port1', 'port2'],
      names: ['name1', 'name2'],
      labels: [
        {key: 'label1', value: 'value1'},
        {key: 'label2', value: 'value2'},
      ],
      localVolumes: 'local-volumes',
      mounts: ['mount1', 'mount2'],
      networks: ['network1', 'network2'],
      runningSince: new Date(999),
      state: ContainerState.RUNNING,
      containerCli: ContainerCli.CRICTL,
    };
    expect(translateContainerDetails(result)).toEqual(expectedResult);
  });

  it('converts optional fields correctly', () => {
    const result: ApiContainerDetails = {};
    const expectedResult: ContainerDetails = {
      containerId: undefined,
      imageName: undefined,
      command: undefined,
      createdAt: undefined,
      status: undefined,
      ports: undefined,
      names: undefined,
      labels: [],
      localVolumes: undefined,
      mounts: undefined,
      networks: undefined,
      runningSince: undefined,
      state: undefined,
      containerCli: undefined,
    };
    expect(translateContainerDetails(result)).toEqual(expectedResult);
  });
});

describe('translateSoftwarePackageInstallState', () => {
  it('converts all fields correctly', () => {
    expect(
      translateSoftwarePackageInstallState(
        ApiSoftwarePackageInstallState.INSTALLED,
      ),
    ).toEqual(SoftwarePackageInstallState.INSTALLED);
    expect(
      translateSoftwarePackageInstallState(
        ApiSoftwarePackageInstallState.PENDING,
      ),
    ).toEqual(SoftwarePackageInstallState.PENDING);
    expect(
      translateSoftwarePackageInstallState(
        ApiSoftwarePackageInstallState.UNINSTALLED,
      ),
    ).toEqual(SoftwarePackageInstallState.UNINSTALLED);
    expect(
      translateSoftwarePackageInstallState(
        ApiSoftwarePackageInstallState.UNKNOWN,
      ),
    ).toEqual(SoftwarePackageInstallState.UNKNOWN);
  });
});

describe('translateSoftwarePackage', () => {
  it('converts all fields correctly', () => {
    const result: ApiSoftwarePackage = {
      name: 'name',
      version: 'version',
      architecture: 'architecture',
      publisher: 'publisher',
      installState: ApiSoftwarePackageInstallState.INSTALLED,
      description: 'description',
      installedOn: '888000',
      installedBy: 'installedBy',
      epoch: 1,
      sourceRpm: 'sourceRpm',
      sourceDeb: 'sourceDeb',
    };
    const expectedResult: SoftwarePackage = {
      name: 'name',
      version: 'version',
      architecture: 'architecture',
      publisher: 'publisher',
      installState: SoftwarePackageInstallState.INSTALLED,
      description: 'description',
      installedOn: new Date(888),
      installedBy: 'installedBy',
      epoch: 1,
      sourceRpm: 'sourceRpm',
      sourceDeb: 'sourceDeb',
    };
    expect(translateSoftwarePackage(result)).toEqual(expectedResult);
  });

  it('converts optional fields correctly', () => {
    const result: ApiSoftwarePackage = {};
    const expectedResult: SoftwarePackage = {
      name: undefined,
      version: undefined,
      architecture: undefined,
      publisher: undefined,
      installState: undefined,
      description: undefined,
      installedOn: undefined,
      installedBy: undefined,
      epoch: undefined,
      sourceRpm: undefined,
      sourceDeb: undefined,
    };
    expect(translateSoftwarePackage(result)).toEqual(expectedResult);
  });
});

describe('translateGetMemorySizeResult', () => {
  it('converts all fields correctly', () => {
    const result: ApiGetMemorySizeResult = {
      totalBytes: '123',
    };
    const expectedResult: GetMemorySizeResult = {
      totalBytes: BigInt(123),
    };
    expect(translateGetMemorySizeResult(result)).toEqual(expectedResult);
  });

  it('converts optional fields correctly', () => {
    const result: ApiGetMemorySizeResult = {};
    const expectedResult: GetMemorySizeResult = {
      totalBytes: undefined,
    };
    expect(translateGetMemorySizeResult(result)).toEqual(expectedResult);
  });
});

describe('isRegistryValue', () => {
  it('returns true if a RegistryValue is passed', () => {
    expect(
      isRegistryValue({
        path: 'foo',
        type: RegistryType.REG_NONE,
        value: {
          string: 'foo',
        },
      }),
    ).toBeTrue();
  });

  it('returns false if a RegistryKey is passed', () => {
    expect(
      isRegistryValue({
        path: 'foo',
        type: 'REG_KEY',
      }),
    ).toBeFalse();
  });
});

describe('translateStatEntry', () => {
  it('converts all fields correctly', () => {
    const statEntry: ApiStatEntry = {
      stMode: '33261',
      stIno: '14157337',
      stDev: '65025',
      stNlink: '1',
      stUid: 610129,
      stGid: 89939,
      stSize: '14',
      stAtime: '1627312917',
      stBtime: '1580294240',
      stMtime: '1580294217',
      stCtime: '1580294236',
      stBlocks: '8',
      stBlksize: '4096',
      stRdev: '0',
      symlink: 'symlink',
      pathspec: {
        pathtype: 'OS' as PathSpecPathType,
        path: '/foo/bar/get_rich_quick.sh',
      },
      stFlagsOsx: 0,
      stFlagsLinux: 524288,
    };
    const result: StatEntry = {
      stMode: BigInt(33261),
      stIno: BigInt(14157337),
      stDev: BigInt(65025),
      stNlink: BigInt(1),
      stUid: 610129,
      stGid: 89939,
      stSize: BigInt(14),
      stAtime: new Date(1627312917000),
      stBtime: new Date(1580294240000),
      stMtime: new Date(1580294217000),
      stCtime: new Date(1580294236000),
      stBlocks: BigInt(8),
      stBlksize: BigInt(4096),
      stRdev: BigInt(0),
      symlink: 'symlink',
      pathspec: {
        pathtype: PathSpecPathType.OS,
        path: '/foo/bar/get_rich_quick.sh',
        segments: [
          {
            pathtype: PathSpecPathType.OS,
            path: '/foo/bar/get_rich_quick.sh',
          },
        ],
      },
      stFlagsOsx: 0,
      stFlagsLinux: 524288,
    };
    expect(translateStatEntry(statEntry)).toEqual(result);
  });

  it('converts optional fields correctly', () => {
    const statEntry: ApiStatEntry = {
      pathspec: {
        pathtype: 'OS' as PathSpecPathType,
        path: '/foo/bar/get_rich_quick.sh',
      },
    };
    const result: StatEntry = {
      pathspec: {
        pathtype: PathSpecPathType.OS,
        path: '/foo/bar/get_rich_quick.sh',
        segments: [
          {
            pathtype: PathSpecPathType.OS,
            path: '/foo/bar/get_rich_quick.sh',
          },
        ],
      },
      stMode: undefined,
      stIno: undefined,
      stDev: undefined,
      stNlink: undefined,
      stUid: undefined,
      stGid: undefined,
      stSize: undefined,
      stAtime: undefined,
      stMtime: undefined,
      stCtime: undefined,
      stBtime: undefined,
      stBlocks: undefined,
      stBlksize: undefined,
      stRdev: undefined,
      stFlagsOsx: undefined,
      stFlagsLinux: undefined,
      symlink: undefined,
    };
    expect(translateStatEntry(statEntry)).toEqual(result);
  });
});

describe('translateBinary', () => {
  it('converts all fields correctly', () => {
    const api: ApiGrrBinary = {
      type: ApiGrrBinaryType.PYTHON_HACK,
      path: 'windows/test/hello.py',
      size: '20746',
      timestamp: '1543574422898113',
      hasValidSignature: true,
    };
    const result: Binary = {
      type: BinaryType.PYTHON_HACK,
      path: 'windows/test/hello.py',
      size: BigInt(20746),
      timestamp: new Date('2018-11-30T10:40:22.898Z'),
    };
    expect(safeTranslateBinary(api)).toEqual(result);
    expect(translateBinary(api)).toEqual(result);
  });

  it('converts optional fields correctly', () => {
    const api: ApiGrrBinary = {
      type: ApiGrrBinaryType.PYTHON_HACK,
      path: 'windows/test/hello.py',
    };
    const result: Binary = {
      type: BinaryType.PYTHON_HACK,
      path: 'windows/test/hello.py',
      size: undefined,
      timestamp: undefined,
    };
    expect(safeTranslateBinary(api)).toEqual(result);
    expect(translateBinary(api)).toEqual(result);
  });

  it('fails for legacy types', () => {
    const api: ApiGrrBinary = {
      type: ApiGrrBinaryType.COMPONENT_DEPRECATED,
      path: 'windows/test/hello.py',
      size: '20746',
      timestamp: '1543574422898113',
      hasValidSignature: true,
    };
    expect(safeTranslateBinary(api)).toBeNull();
    expect(() => translateBinary(api)).toThrowError(
      PreconditionError,
      /Expected .*COMPONENT_DEPRECATED.* to be a member of enum.*PYTHON_HACK/,
    );
  });
});
