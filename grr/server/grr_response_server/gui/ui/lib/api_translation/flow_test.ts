import {ApiFlow, ApiFlowResult, ApiFlowState, PathSpecPathType, RegistryType as ApiRegistryType} from '@app/lib/api/api_interfaces';
import {newPathSpec} from '@app/lib/api/api_test_util';
import {Flow, FlowResult, FlowState, RegistryType} from '@app/lib/models/flow';

import {initTestEnvironment} from '../../testing';

import {translateFlow, translateFlowResult, translateHashToHex, translateStatEntry} from './flow';



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
    };

    expect(translateFlow(apiFlow)).toEqual(flow);
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
    const base64 = encodeBase64([0x12, 0xFE, 0x55]);
    expect(translateHashToHex({md5: base64})).toEqual(jasmine.objectContaining({
      md5: '12fe55'
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

describe('translateStatEntry', () => {
  it('returns the original StatEntry as fallback', () => {
    expect(translateStatEntry({
      pathspec: {path: 'foo'},
      stBlksize: 4,
    })).toEqual({
      pathspec: {path: 'foo'},
      stBlksize: 4,
    });
  });

  it('returns a RegistryValue if registryType is set', () => {
    expect(translateStatEntry({
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
       expect(translateStatEntry({
         pathspec: {path: 'foo', pathtype: PathSpecPathType.REGISTRY},
       })).toEqual({
         path: 'foo',
         type: 'REG_KEY',
       });
     });
});
