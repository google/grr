import * as api from '@app/lib/api/api_interfaces';
import {ApiFlow, ApiFlowResult, ApiFlowState} from '@app/lib/api/api_interfaces';
import {newPathSpec} from '@app/lib/api/api_test_util';
import {ArtifactDescriptor, Flow, FlowResult, FlowState, OperatingSystem, SourceType} from '@app/lib/models/flow';

import {initTestEnvironment} from '../../testing';

import {translateArtifactDescriptor, translateFlow, translateFlowResult, translateHashToHex} from './flow';



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
        '@type': 'StatEntry',
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

describe('translateArtifactDescriptor', () => {
  it('correctly translates API data', () => {
    const apiResponse: api.ArtifactDescriptor = {
      'artifact': {
        'name': 'ChromeHistory',
        'doc': 'Chrome browser history.',
        'labels': ['Browser'],
        'supportedOs': ['Windows', 'Linux'],
        'urls': ['artifactUrl'],
        'sources': [
          {
            'type': 'FILE' as SourceType,
            'attributes': {
              'dat': [
                {
                  'k': {'string': 'paths'},
                  'v': {
                    'list': {
                      'content': [
                        {'string': 'windowsPath1'},
                        {'string': 'windowsPath2'},
                      ]
                    }
                  }
                },
                {'k': {'string': 'separator'}, 'v': {'string': '\\'}}
              ]
            },
            'supportedOs': ['Windows']
          },
          {
            'type': 'FILE' as SourceType,
            'attributes': {
              'dat': [{
                'k': {'string': 'paths'},
                'v': {
                  'list': {
                    'content': [
                      {'string': 'linuxPath1'},
                      {'string': 'linuxPath2'},
                    ]
                  }
                }
              }]
            },
            'supportedOs': ['Linux']
          }
        ]
      },
      'pathDependencies': ['users.homedir', 'users.localappdata'],
      'isCustom': false,
    };

    const descriptor: ArtifactDescriptor = {
      name: 'ChromeHistory',
      doc: 'Chrome browser history.',
      labels: ['Browser'],
      supportedOs: new Set([OperatingSystem.WINDOWS, OperatingSystem.LINUX]),
      urls: ['artifactUrl'],
      provides: [],
      dependencies: [],
      sources: [
        {
          type: SourceType.FILE,
          attributes: new Map(Object.entries({
            paths: ['windowsPath1', 'windowsPath2'],
            separator: '\\',
          })),
          supportedOs: new Set([OperatingSystem.WINDOWS]),
          conditions: [],
          returnedTypes: [],
        },
        {
          type: SourceType.FILE,
          attributes: new Map(Object.entries({
            paths: ['linuxPath1', 'linuxPath2'],
          })),
          supportedOs: new Set([OperatingSystem.LINUX]),
          conditions: [],
          returnedTypes: [],
        }
      ],
      pathDependencies: ['users.homedir', 'users.localappdata'],
      isCustom: false,
    };

    expect(translateArtifactDescriptor(apiResponse)).toEqual(descriptor);
  });
});
