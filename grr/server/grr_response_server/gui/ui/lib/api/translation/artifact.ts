import {
  ArtifactDescriptor,
  ArtifactDescriptorMap,
  ArtifactSourceDescription,
  SourceType,
} from '../../models/flow';
import {assertKeyNonNull} from '../../preconditions';
import {
  ArtifactDescriptor as ApiArtifactDescriptor,
  ArtifactSource as ApiArtifactSource,
  Artifact,
  ArtifactSourceSourceType,
} from '../api_interfaces';
import {safeTranslateOperatingSystem} from './flow';
import {translateDict} from './primitive';

function getArtifactSourceDescription(
  source: ApiArtifactSource,
): ArtifactSourceDescription {
  assertKeyNonNull(source, 'type');
  // Artifact groups are handled separately outside this function.
  if (source.type === ArtifactSourceSourceType.ARTIFACT_GROUP) {
    throw new Error('Artifact group sources are not supported');
  }

  const supportedOsList = (source.supportedOs ?? [])
    .map(safeTranslateOperatingSystem)
    .filter((os) => os != null);

  const attributes = translateDict(source.attributes ?? {}) as ReadonlyMap<
    string,
    unknown
  >;

  switch (source.type) {
    case ArtifactSourceSourceType.COMMAND:
      const cmd = attributes.get('cmd') as string;
      const args = (attributes.get('args') as string[]) ?? [];
      return {
        type: SourceType.COMMAND,
        supportedOs: new Set(supportedOsList),
        collections: [[cmd, ...args].join(' ')],
      };
    case ArtifactSourceSourceType.FILE:
      return {
        type: SourceType.FILE,
        supportedOs: new Set(supportedOsList),
        collections: attributes.get('paths') as string[],
      };
    case ArtifactSourceSourceType.PATH:
      return {
        type: SourceType.PATH,
        supportedOs: new Set(supportedOsList),
        collections: attributes.get('paths') as string[],
      };
    case ArtifactSourceSourceType.REGISTRY_KEY:
      return {
        type: SourceType.REGISTRY_KEY,
        supportedOs: new Set(supportedOsList),
        collections: attributes.get('keys') as string[],
      };
    case ArtifactSourceSourceType.REGISTRY_VALUE:
      const pairs =
        (attributes.get('key_value_pairs') as Array<
          Map<'key' | 'value', string>
        >) ?? [];
      const values = pairs.map((p) => `${p.get('key')}\\${p.get('value')}`);
      return {
        type: SourceType.REGISTRY_VALUE,
        supportedOs: new Set(supportedOsList),
        collections: values,
      };
    case ArtifactSourceSourceType.WMI:
      return {
        type: SourceType.WMI,
        supportedOs: new Set(supportedOsList),
        collections: [attributes.get('query') as string],
      };
    default:
      return {
        type: SourceType.COLLECTOR_TYPE_UNKNOWN,
        supportedOs: new Set(supportedOsList),
        collections: [],
      };
  }
}

/**
 * Recursively translates an API ArtifactDescriptor and its contained Group
 * Artifacts into a single ArtifactDescriptor.
 */
export function translateArtifactDescriptorRecursively(
  artifactNameToTranslate: string,
  apiAds: readonly ApiArtifactDescriptor[],
): ArtifactDescriptor {
  let apiDescriptor: ApiArtifactDescriptor | undefined = undefined;
  for (const descriptor of apiAds) {
    if (descriptor.artifact?.name === artifactNameToTranslate) {
      apiDescriptor = descriptor;
      break;
    }
    if (descriptor.artifact?.aliases?.includes(artifactNameToTranslate)) {
      apiDescriptor = descriptor;
      break;
    }
  }
  if (!apiDescriptor) {
    throw new Error(`Artifact with name ${artifactNameToTranslate} not found`);
  }
  const artifact: Artifact = apiDescriptor?.artifact ?? {};

  const descriptions: ArtifactSourceDescription[] = [];
  const recursiveSources: ArtifactDescriptor[] = [];
  for (const source of artifact.sources ?? []) {
    assertKeyNonNull(source, 'type');
    if (source.type === ArtifactSourceSourceType.ARTIFACT_GROUP) {
      // Recursively add all artifacts from the group
      const attributes = translateDict(source.attributes ?? {}) as ReadonlyMap<
        string,
        string
      >;

      for (const name of attributes.get('names') ?? []) {
        recursiveSources.push(
          translateArtifactDescriptorRecursively(name, apiAds),
        );
      }
    } else {
      descriptions.push(getArtifactSourceDescription(source));
    }
  }
  assertKeyNonNull(artifact, 'name');
  return {
    name: artifact.name,
    doc: artifact.doc,
    supportedOs: new Set(
      [...(artifact.supportedOs ?? [])]
        .map(safeTranslateOperatingSystem)
        .filter((os) => os != null),
    ),
    urls: [...(artifact.urls ?? [])],
    isCustom: apiDescriptor.isCustom ?? false,
    pathDependencies: [...(apiDescriptor.pathDependencies ?? [])],
    dependencies: [...(apiDescriptor.dependencies ?? [])],
    artifacts: recursiveSources,
    sourceDescriptions: descriptions,
  };
}

/**
 * Flattens an API ArtifactDescriptor and its contained Artifact into one
 * object.
 */
export function translateArtifactDescriptors(
  ads: readonly ApiArtifactDescriptor[],
): ArtifactDescriptorMap {
  const result = new Map<string, ArtifactDescriptor>();

  for (const ad of ads) {
    assertKeyNonNull(ad, 'artifact');
    const artifact = ad.artifact;
    assertKeyNonNull(artifact, 'name');
    const name = artifact.name;
    result.set(name, translateArtifactDescriptorRecursively(name, ads));
  }

  return result;
}
