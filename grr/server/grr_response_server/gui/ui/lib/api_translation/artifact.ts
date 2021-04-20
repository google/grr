import * as api from '@app/lib/api/api_interfaces';
import {translateDict} from '@app/lib/api_translation/primitive';
import {ArtifactDescriptor, ArtifactSource, OperatingSystem, SourceType} from '@app/lib/models/flow';

import {assertKeyNonNull, PreconditionError} from '../preconditions';

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
    labels: [...artifact.labels ?? []],
    supportedOs:
        new Set([...artifact.supportedOs ?? []].map(translateOperatingSystem)),
    urls: [...artifact.urls ?? []],
    provides: [...artifact.provides ?? []],
    dependencies: [...ad.dependencies ?? []],
    pathDependencies: [...ad.pathDependencies ?? []],
    isCustom: ad.isCustom ?? false,
    sources: [...artifact.sources ?? []].map(translateArtifactSource),
  };
}

function translateOperatingSystem(str: string): OperatingSystem {
  switch (str) {
    case 'Linux':
      return OperatingSystem.LINUX;
    case 'Darwin':
      return OperatingSystem.DARWIN;
    case 'Windows':
      return OperatingSystem.WINDOWS;
    default:
      throw new PreconditionError(
          `OperatingSystem enum does not include "${str}".`);
  }
}

/** Translates a String to OperatingSystem, returning undefined on error. */
export function safeTranslateOperatingSystem(str: string|undefined):
    OperatingSystem|undefined {
  if (str === undefined) {
    return undefined;
  }

  try {
    return translateOperatingSystem(str);
  } catch (e: unknown) {
    return undefined;
  }
}

type KeyValuePair = Map<'key'|'value', string>;

function translateArtifactSource(source: api.ArtifactSource): ArtifactSource {
  assertKeyNonNull(source, 'type');

  const attributes =
      translateDict(source.attributes ?? {}) as ReadonlyMap<string, unknown>;

  const base = {
    conditions: [...source.conditions ?? []],
    returnedTypes: [...source.returnedTypes ?? []],
    supportedOs:
        new Set([...source.supportedOs ?? []].map(translateOperatingSystem)),
  };

  switch (source.type) {
    case api.SourceType.ARTIFACT_GROUP:
      return {
        ...base,
        type: SourceType.ARTIFACT_GROUP,
        names: attributes.get('names') as string[] ?? [],
      };

    case api.SourceType.ARTIFACT_FILES:
      return {
        ...base,
        type: SourceType.ARTIFACT_FILES,
        names: attributes.get('artifact_list') as string[] ?? [],
      };

    case api.SourceType.GRR_CLIENT_ACTION:
      return {
        ...base,
        type: SourceType.GRR_CLIENT_ACTION,
        clientAction: attributes.get('client_action') as string,
      };

    case api.SourceType.COMMAND:
      const cmd = attributes.get('cmd') as string;
      const args = attributes.get('args') as string[] ?? [];
      return {
        ...base,
        type: SourceType.COMMAND,
        cmdline: [cmd, ...args].join(' '),
      };

    case api.SourceType.DIRECTORY:
      return {
        ...base,
        type: SourceType.DIRECTORY,
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.SourceType.FILE:
      return {
        ...base,
        type: SourceType.FILE,
        paths: attributes.get('paths') as string[] ?? [],
      };
    case api.SourceType.GREP:
      return {
        ...base,
        type: SourceType.GREP,
        // TODO(user): Add grep param.
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.SourceType.PATH:
      return {
        ...base,
        type: SourceType.PATH,
        paths: attributes.get('paths') as string[] ?? [],
      };

    case api.SourceType.REGISTRY_KEY:
      return {
        ...base,
        type: SourceType.REGISTRY_KEY,
        keys: attributes.get('keys') as string[] ?? [],
      };

    case api.SourceType.REGISTRY_VALUE:
      const pairs = attributes.get('key_value_pairs') as KeyValuePair[] ?? [];
      const values = pairs.map((p) => `${p.get('key')}\\${p.get('value')}`);

      return {
        ...base,
        type: SourceType.REGISTRY_VALUE,
        values,
      };

    case api.SourceType.WMI:
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
