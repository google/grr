import {ApiFlow, ApiFlowResult, ApiFlowState, ApiGrrBinary, ApiGrrBinaryType, PathSpecPathType, StatEntry as ApiStatEntry, StatEntryRegistryType as ApiRegistryType} from '../../lib/api/api_interfaces';
import {newPathSpec} from '../../lib/api/api_test_util';
import {Binary, BinaryType, Flow, FlowResult, FlowState, RegistryType} from '../../lib/models/flow';
import {initTestEnvironment, removeUndefinedKeys} from '../../testing';
import {StatEntry} from '../models/vfs';
import {PreconditionError} from '../preconditions';

import {safeTranslateBinary, translateBinary, translateFlow, translateFlowResult, translateHashToHex, translateStatEntry, translateVfsStatEntry} from './flow';



initTestEnvironment();

describe('Flow API Translation', () => {
  it('converts populated ApiFlow correctly', () => {
    const apiFlow: ApiFlow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'KeepAlive',
      creator: 'morty',
      lastActiveAt: '1571789996681000',  // 2019-10-23T00:19:56.681Z
      startedAt: '1571789996679000',     // 2019-10-23T00:19:56.679Z
      state: ApiFlowState.TERMINATED,
      isRobot: false,
    };

    const flow: Flow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'KeepAlive',
      creator: 'morty',
      lastActiveAt: new Date(1571789996681),
      startedAt: new Date(1571789996679),
      args: undefined,
      progress: undefined,
      state: FlowState.FINISHED,
      errorDescription: undefined,
      resultCounts: undefined,
      isRobot: false,
    };

    expect(translateFlow(apiFlow)).toEqual(flow);
  });

  it('converts CLIENT_TERMINATED status to ERROR', () => {
    const apiFlow: ApiFlow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'KeepAlive',
      creator: 'morty',
      lastActiveAt: '1571789996681000',  // 2019-10-23T00:19:56.681Z
      startedAt: '1571789996679000',     // 2019-10-23T00:19:56.679Z
      state: ApiFlowState.CLIENT_CRASHED,
      isRobot: false,
    };

    expect(translateFlow(apiFlow)).toEqual(jasmine.objectContaining({
      state: FlowState.ERROR
    }));
  });
});

describe('ApiFlowResult translation', () => {
  it('converts ApiFlowResult to FlowResult correctly', () => {
    const apiFlowResult: ApiFlowResult = {
      payload: {
        '@type': 'example.com/grr.StatEntry',
        path: newPathSpec('/foo/bar'),
      },
      payloadType: 'StatEntry',
      timestamp: '1571789996681000',  // 2019-10-23T00:19:56.681Z
      tag: 'someTag'
    };

    const flowResult: FlowResult = {
      payload: {
        path: newPathSpec('/foo/bar'),
      },
      payloadType: 'StatEntry',
      tag: 'someTag',
      timestamp: new Date(1571789996681),
    };

    expect(translateFlowResult(apiFlowResult)).toEqual(flowResult);
  });
});

function encodeBase64(bytes: number[]): string {
  return btoa(bytes.map(b => String.fromCharCode(b)).join(''));
}

describe('translateHashToHex', () => {
  it('translates an empty object to an empty object', () => {
    expect(translateHashToHex({})).toEqual(jasmine.objectContaining({}));
  });

  it('converts base64-encoded bytes to hex', () => {
    const base64 = '0h4jIWBHN0HOLBVJnSZhJg==';
    expect(translateHashToHex({md5: base64})).toEqual(jasmine.objectContaining({
      md5: 'd21e232160473741ce2c15499d266126'
    }));
  });

  it('converts sha1, sha256, and md5', () => {
    expect(translateHashToHex({
      md5: encodeBase64([0x12]),
      sha1: encodeBase64([0x34]),
      sha256: encodeBase64([0x56])
    })).toEqual({
      md5: '12',
      sha1: '34',
      sha256: '56',
    });
  });
});

describe('translateVfsStatEntry', () => {
  it('returns a StatEntry as fallback', () => {
    expect(removeUndefinedKeys(translateVfsStatEntry({
      pathspec: {path: 'foo', pathtype: 'OS' as PathSpecPathType},
    }))).toEqual({
      pathspec: {
        path: 'foo',
        pathtype: PathSpecPathType.OS,
        segments: [{path: 'foo', pathtype: PathSpecPathType.OS}],
      },
    });
  });

  it('returns a RegistryValue if registryType is set', () => {
    expect(translateVfsStatEntry({
      pathspec: {path: 'foo', pathtype: PathSpecPathType.REGISTRY},
      registryType: ApiRegistryType.REG_NONE,
      stSize: '123',
    })).toEqual({
      path: 'foo',
      type: RegistryType.REG_NONE,
      size: BigInt(123),
    });
  });

  it('returns a RegistryKey for non-Registry-Values with PathType REGISTRY',
     () => {
       expect(translateVfsStatEntry({
         pathspec: {path: 'foo', pathtype: PathSpecPathType.REGISTRY},
       })).toEqual({
         path: 'foo',
         type: 'REG_KEY',
       });
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
      stMtime: '1580294217',
      stCtime: '1580294236',
      stBlocks: '8',
      stBlksize: '4096',
      stRdev: '0',
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
      stMtime: new Date(1580294217000),
      stCtime: new Date(1580294236000),
      stBlocks: BigInt(8),
      stBlksize: BigInt(4096),
      stRdev: BigInt(0),
      pathspec: {
        pathtype: PathSpecPathType.OS,
        path: '/foo/bar/get_rich_quick.sh',
        segments: [{
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
        }]
      },
      stFlagsOsx: 0,
      stFlagsLinux: 524288
    };
    expect(removeUndefinedKeys(translateStatEntry(statEntry))).toEqual(result);
  });

  it('converts optional fields correctly', () => {
    const statEntry: ApiStatEntry = {
      pathspec: {
        pathtype: 'OS' as PathSpecPathType,
        path: '/foo/bar/get_rich_quick.sh',
      }
    };
    const result: StatEntry = {
      pathspec: {
        pathtype: PathSpecPathType.OS,
        path: '/foo/bar/get_rich_quick.sh',
        segments: [{
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
        }],
      },
    };
    expect(removeUndefinedKeys(translateStatEntry(statEntry))).toEqual(result);
  });
});

describe('translateBinary', () => {
  it('converts all fields correctly', () => {
    const api: ApiGrrBinary = {
      type: ApiGrrBinaryType.PYTHON_HACK,
      path: 'windows/test/hello.py',
      size: '20746',
      timestamp: '1543574422898113',
      hasValidSignature: true
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

  it('fails for legacy types', () => {
    const api: ApiGrrBinary = {
      type: ApiGrrBinaryType.COMPONENT_DEPRECATED,
      path: 'windows/test/hello.py',
      size: '20746',
      timestamp: '1543574422898113',
      hasValidSignature: true
    };
    expect(safeTranslateBinary(api)).toBeNull();
    expect(() => translateBinary(api))
        .toThrowError(
            PreconditionError,
            /Expected .*COMPONENT_DEPRECATED.* to be a member of enum.*PYTHON_HACK/);
  });
});
