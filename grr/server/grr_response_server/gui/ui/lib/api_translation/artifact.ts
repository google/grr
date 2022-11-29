import * as api from '../../lib/api/api_interfaces';
import {translateDict} from '../../lib/api_translation/primitive';
import {ArtifactDescriptor, ArtifactSource, SourceType} from '../../lib/models/flow';
import {assertKeyNonNull, isNonNull} from '../preconditions';

import {safeTranslateOperatingSystem} from './flow';

/**
 * Flattens an API ArtifactDescriptor and its contained Artifact into one
 * object.
 */
export function translateArtifactDescriptor(ad: api.ArtifactDescriptor):
    ArtifactDescriptor {
  assertKeyNonNull(ad, 'artifact');
  const artifact = ad.artifact ?? {};

  assertKeyNonNull(artifact, 'name');

  return {
    name: artifact.name,
    doc: artifact.doc,
    supportedOs: new Set([...artifact.supportedOs ?? []]
                             .map(safeTranslateOperatingSystem)
                             .filter(isNonNull)),
    urls: [...artifact.urls ?? []],
    provides: [...artifact.provides ?? []],
    dependencies: [...ad.dependencies ?? []],
    pathDependencies: [...ad.pathDependencies ?? []],
    isCustom: ad.isCustom ?? false,
    sources: [...artifact.sources ?? []].map(translateArtifactSource),
  };
}

type KeyValuePair = Map<'key'|'value', string>;

function translateArtifactSource(source: api.ArtifactSource): ArtifactSource {
  assertKeyNonNull(source, 'type');

  const attributes =
      translateDict(source.attributes ?? {}) as ReadonlyMap<string, unknown>;

  const base = {
    conditions: [...source.conditions ?? []],
    returnedTypes: [...source.returnedTypes ?? []],
    supportedOs: new Set([...source.supportedOs ?? []]
                             .map(safeTranslateOperatingSystem)
                             .filter(isNonNull)),
  };

  switch (source.type) {
    case api.ArtifactSourceSourceType.ARTIFACT_GROUP:
      return {
        ...base,
        type: SourceType.ARTIFACT_GROUP,
        names: attributes.get('names') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.ARTIFACT_FILES:
      return {
        ...base,
        type: SourceType.ARTIFACT_FILES,
        names: attributes.get('artifact_list') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.GRR_CLIENT_ACTION:
      return {
        ...base,
        type: SourceType.GRR_CLIENT_ACTION,
        clientAction: attributes.get('client_action') as string,
      };

    case api.ArtifactSourceSourceType.COMMAND:
      const cmd = attributes.get('cmd') as string;
      const args = attributes.get('args') as string[] ?? [];
      return {
        ...base,
        type: SourceType.COMMAND,
        cmdline: [cmd, ...args].join(' '),
      };

    case api.ArtifactSourceSourceType.DIRECTORY:
      return {
        ...base,
        type: SourceType.DIRECTORY,
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.FILE:
      return {
        ...base,
        type: SourceType.FILE,
        paths: attributes.get('paths') as string[] ?? [],
      };
    case api.ArtifactSourceSourceType.GREP:
      return {
        ...base,
        type: SourceType.GREP,
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.PATH:
      return {
        ...base,
        type: SourceType.PATH,
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.REGISTRY_KEY:
      return {
        ...base,
        type: SourceType.REGISTRY_KEY,
        keys: attributes.get('keys') as string[] ?? [],
      };

    case api.ArtifactSourceSourceType.REGISTRY_VALUE:
      const pairs = attributes.get('key_value_pairs') as KeyValuePair[] ?? [];
      const values = pairs.map((p) => `${p.get('key')}\\${p.get('value')}`);

      return {
        ...base,
        type: SourceType.REGISTRY_VALUE,
        values,
      };

    case api.ArtifactSourceSourceType.WMI:
      return {
        ...base,
        type: SourceType.WMI,
        query: attributes.get('query') as string,
      };

    default:
      return {
        ...base,
        type: SourceType.COLLECTOR_TYPE_UNKNOWN,
      };
  }
}
