import * as api from '../../lib/api/api_interfaces';
import {ArtifactDescriptor, OperatingSystem, SourceType} from '../../lib/models/flow';
import {initTestEnvironment} from '../../testing';

import {translateArtifactDescriptor} from './artifact';



initTestEnvironment();

describe('translateArtifactDescriptor', () => {
  it('correctly translates API data', () => {
    const apiResponse: api.ArtifactDescriptor = {
      'artifact': {
        'name': 'ChromiumBasedBrowsersHistory',
        'doc': 'Chrome browser history.',
        'supportedOs': ['Windows', 'Linux'],
        'urls': ['artifactUrl'],
        'sources': [
          {
            'type': 'FILE' as api.ArtifactSourceSourceType,
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
            'type': 'FILE' as api.ArtifactSourceSourceType,
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
      name: 'ChromiumBasedBrowsersHistory',
      doc: 'Chrome browser history.',
      supportedOs: new Set([OperatingSystem.WINDOWS, OperatingSystem.LINUX]),
      urls: ['artifactUrl'],
      provides: [],
      dependencies: [],
      sources: [
        {
          type: SourceType.FILE,
          paths: ['windowsPath1', 'windowsPath2'],
          supportedOs: new Set([OperatingSystem.WINDOWS]),
          conditions: [],
          returnedTypes: [],
        },
        {
          type: SourceType.FILE,
          paths: ['linuxPath1', 'linuxPath2'],
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
