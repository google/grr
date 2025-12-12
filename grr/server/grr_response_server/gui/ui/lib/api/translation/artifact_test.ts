import {initTestEnvironment} from '../../../testing';
import {
  ArtifactDescriptor,
  OperatingSystem,
  SourceType,
} from '../../models/flow';
import * as api from '../api_interfaces';
import {
  translateArtifactDescriptorRecursively,
  translateArtifactDescriptors,
} from './artifact';

initTestEnvironment();

describe('translateArtifactDescriptor', () => {
  it('correctly translates API data', () => {
    const apiResponse: api.ArtifactDescriptor[] = [
      {
        'artifact': {
          'name': 'ChromiumBasedBrowsersHistoryDatabaseFile',
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
                        ],
                      },
                    },
                  },
                  {'k': {'string': 'separator'}, 'v': {'string': '\\'}},
                ],
              },
              'supportedOs': ['Windows'],
            },
            {
              'type': 'FILE' as api.ArtifactSourceSourceType,
              'attributes': {
                'dat': [
                  {
                    'k': {'string': 'paths'},
                    'v': {
                      'list': {
                        'content': [
                          {'string': 'linuxPath1'},
                          {'string': 'linuxPath2'},
                        ],
                      },
                    },
                  },
                ],
              },
              'supportedOs': ['Linux'],
            },
          ],
        },
        'pathDependencies': ['users.homedir', 'users.localappdata'],
        'isCustom': false,
      },
      {
        'artifact': {
          'name': 'RecursiveArtifact',
          'doc': 'recursive artifact.',
          'supportedOs': ['Windows', 'Darwin'],
          'urls': ['artifactUrl'],
          'sources': [
            {
              'type': 'ARTIFACT_GROUP' as api.ArtifactSourceSourceType,
              'attributes': {
                'dat': [
                  {
                    'k': {'string': 'names'},
                    'v': {
                      'list': {
                        'content': [
                          {
                            'string':
                              'ChromiumBasedBrowsersHistoryDatabaseFile',
                          },
                        ],
                      },
                    },
                  },
                ],
              },
              'supportedOs': ['Linux'],
            },
          ],
        },
        'pathDependencies': ['users.homedir'],
        'isCustom': false,
      },
    ];
    const expected = new Map<string, ArtifactDescriptor>();
    expected.set('ChromiumBasedBrowsersHistoryDatabaseFile', {
      name: 'ChromiumBasedBrowsersHistoryDatabaseFile',
      doc: 'Chrome browser history.',
      supportedOs: new Set([OperatingSystem.WINDOWS, OperatingSystem.LINUX]),
      urls: ['artifactUrl'],
      artifacts: [],
      sourceDescriptions: [
        {
          type: SourceType.FILE,
          collections: ['windowsPath1', 'windowsPath2'],
          supportedOs: new Set([OperatingSystem.WINDOWS]),
        },
        {
          type: SourceType.FILE,
          collections: ['linuxPath1', 'linuxPath2'],
          supportedOs: new Set([OperatingSystem.LINUX]),
        },
      ],
      pathDependencies: ['users.homedir', 'users.localappdata'],
      dependencies: [],
      isCustom: false,
    });
    expected.set('RecursiveArtifact', {
      name: 'RecursiveArtifact',
      doc: 'recursive artifact.',
      supportedOs: new Set([OperatingSystem.WINDOWS, OperatingSystem.DARWIN]),
      urls: ['artifactUrl'],
      sourceDescriptions: [],
      pathDependencies: ['users.homedir'],
      dependencies: [],
      isCustom: false,
      artifacts: [
        {
          name: 'ChromiumBasedBrowsersHistoryDatabaseFile',
          doc: 'Chrome browser history.',
          supportedOs: new Set([
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
          ]),
          urls: ['artifactUrl'],
          artifacts: [],
          sourceDescriptions: [
            {
              type: SourceType.FILE,
              collections: ['windowsPath1', 'windowsPath2'],
              supportedOs: new Set([OperatingSystem.WINDOWS]),
            },
            {
              type: SourceType.FILE,
              collections: ['linuxPath1', 'linuxPath2'],
              supportedOs: new Set([OperatingSystem.LINUX]),
            },
          ],
          pathDependencies: ['users.homedir', 'users.localappdata'],
          dependencies: [],
          isCustom: false,
        },
      ],
    });

    expect(translateArtifactDescriptors(apiResponse)).toEqual(expected);
  });

  describe('translateArtifactDescriptorRecursively', () => {
    it('throws error if artifact is not found', () => {
      const apiResponse: api.ArtifactDescriptor[] = [];
      expect(() =>
        translateArtifactDescriptorRecursively('ArtifactName', apiResponse),
      ).toThrowError('Artifact with name ArtifactName not found');
    });

    it('correctly translates artifact data based on artifact name', () => {
      const apiResponse: api.ArtifactDescriptor[] = [
        {
          'artifact': {
            'name': 'ArtifactName',
            'doc': 'Artifact description.',
          },
        },
      ];

      const result = translateArtifactDescriptorRecursively(
        'ArtifactName',
        apiResponse,
      );
      expect(result).toEqual({
        name: 'ArtifactName',
        doc: 'Artifact description.',
        supportedOs: new Set(),
        urls: [],
        isCustom: false,
        pathDependencies: [],
        dependencies: [],
        artifacts: [],
        sourceDescriptions: [],
      });
    });

    it('correctly translates artifact data based on artifact alias', () => {
      const apiResponse: api.ArtifactDescriptor[] = [
        {
          'artifact': {
            'name': 'ArtifactName',
            'doc': 'Artifact description.',
            'aliases': ['ArtifactAlias1', 'ArtifactAlias2'],
          },
        },
      ];

      const result = translateArtifactDescriptorRecursively(
        'ArtifactAlias1',
        apiResponse,
      );
      expect(result).toEqual({
        name: 'ArtifactName',
        doc: 'Artifact description.',
        supportedOs: new Set(),
        urls: [],
        isCustom: false,
        pathDependencies: [],
        dependencies: [],
        artifacts: [],
        sourceDescriptions: [],
      });
    });
  });
});
