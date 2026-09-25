import {extendArtifactDescriptor, isFlowResult, OperatingSystem} from './flow';
import {
  newArtifactDescriptor,
  newArtifactSourceDescription,
  newFlowResult,
  newHuntResult,
} from './model_test_util';

describe('Flow model', () => {
  it('isFlowResult', () => {
    expect(isFlowResult(newFlowResult({tag: 'foo'}))).toBeTrue();
    expect(isFlowResult(newHuntResult({}))).toBeFalse();
  });

  it('extendArtifactDescriptor with client OS', () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'artifact',
      doc: 'artifact doc',
      supportedOs: new Set([OperatingSystem.WINDOWS]),
      urls: ['url1', 'url2'],
      dependencies: ['dependency1', 'dependency2'],
      pathDependencies: ['path_dependency1', 'path_dependency2'],
      sourceDescriptions: [
        newArtifactSourceDescription({
          collections: ['source1', 'source2'],
        }),
        newArtifactSourceDescription({
          collections: ['source3', 'source4'],
        }),
      ],
      artifacts: [
        newArtifactDescriptor({
          name: 'nested_artifact1',
        }),
        newArtifactDescriptor({
          name: 'nested_artifact2',
        }),
      ],
      isCustom: true,
    });

    const extendedArtifactDescriptor = extendArtifactDescriptor(
      artifactDescriptor,
      OperatingSystem.DARWIN,
    );

    expect(extendedArtifactDescriptor.name).toBe('artifact');
    expect(extendedArtifactDescriptor.firstArtifactCollection).toBe('source1');
    expect(extendedArtifactDescriptor.numSources).toBe(2);
    expect(extendedArtifactDescriptor.availableOnClient).toBeFalse();
    expect(extendedArtifactDescriptor.matchesInput('artifact')).toBeTrue();
    expect(extendedArtifactDescriptor.matchesInput('artifact doc')).toBeTrue();
    expect(extendedArtifactDescriptor.matchesInput('windows')).toBeTrue();
    expect(extendedArtifactDescriptor.matchesInput('source1')).toBeTrue();
    expect(extendedArtifactDescriptor.matchesInput('unknown')).toBeFalse();
  });

  it('extendArtifactDescriptor without client OS defaults to available on client', () => {
    const artifactDescriptor = newArtifactDescriptor({});

    const extendedArtifactDescriptor =
      extendArtifactDescriptor(artifactDescriptor);

    expect(extendedArtifactDescriptor.availableOnClient).toBeTrue();
  });
});
