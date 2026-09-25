import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ArtifactDescriptor,
  OperatingSystem,
  SourceType,
} from '../../lib/models/flow';
import {
  newArtifactDescriptor,
  newArtifactSourceDescription,
} from '../../lib/models/model_test_util';
import {initTestEnvironment} from '../../testing';
import {ArtifactDetails} from './artifact_details';
import {ArtifactDetailsHarness} from './testing/artifact_details_harness';

initTestEnvironment();

async function createComponent(artifact: ArtifactDescriptor) {
  const fixture = TestBed.createComponent(ArtifactDetails);
  fixture.componentRef.setInput('artifact', artifact);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ArtifactDetailsHarness,
  );
  return {fixture, harness};
}

describe('Artifact Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ArtifactDetails, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent(newArtifactDescriptor({}));

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('displays the artifact details', async () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'Shopping List',
      doc: 'artifact1 doc',
      supportedOs: new Set([OperatingSystem.LINUX]),
      artifacts: [
        newArtifactDescriptor({
          name: 'Veggies',
          supportedOs: new Set([OperatingSystem.LINUX]),

          sourceDescriptions: [
            newArtifactSourceDescription({
              type: SourceType.FILE,
              supportedOs: new Set([OperatingSystem.LINUX]),
              collections: ['Cucumber'],
            }),
          ],
        }),
        newArtifactDescriptor({
          name: 'Fruits',
          supportedOs: new Set([OperatingSystem.LINUX]),
          sourceDescriptions: [
            newArtifactSourceDescription({
              type: SourceType.REGISTRY_KEY,
              supportedOs: new Set([OperatingSystem.LINUX]),
              collections: ['Apple', 'Banana'],
            }),
          ],
          artifacts: [
            newArtifactDescriptor({
              name: 'Exotic Fruits',
              supportedOs: new Set([OperatingSystem.LINUX]),
              sourceDescriptions: [
                newArtifactSourceDescription({
                  type: SourceType.FILE,
                  supportedOs: new Set([OperatingSystem.LINUX]),
                  collections: ['Mango'],
                }),
              ],
            }),
          ],
        }),
      ],
    });
    const {harness} = await createComponent(artifactDescriptor);

    const artifactTree = await harness.matTreeHarness();

    let artifactTreeNodes = await artifactTree.getNodes();
    expect(artifactTreeNodes.length).toBe(1);
    await artifactTreeNodes[0].expand();
    artifactTreeNodes = await artifactTree.getNodes();

    const shoppingListNode = artifactTreeNodes[0];
    expect(await shoppingListNode.getText()).toContain('Shopping List');

    const veggiesListNode = artifactTreeNodes[1];
    expect(await veggiesListNode?.getText()).toContain('Veggies');
    expect(await veggiesListNode?.getText()).toContain('Cucumber');

    const fruitsListNode = artifactTreeNodes[2];
    expect(await fruitsListNode?.getText()).toContain('Fruits');
    expect(await fruitsListNode?.getText()).toContain('Apple');
    expect(await fruitsListNode?.getText()).toContain('Banana');

    const exoticFruitsListNode = artifactTreeNodes[3];
    expect(await exoticFruitsListNode?.getText()).toContain('Exotic Fruits');
    expect(await exoticFruitsListNode?.getText()).toContain('Mango');
  });

  it('displays the artifact references', async () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'Test Artifact',
      urls: ['https://test.com'],
    });
    const {harness} = await createComponent(artifactDescriptor);

    expect(await harness.getReferences()).toContain('https://test.com');
  });

  it('displays the artifact supported OS', async () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'Test Artifact',
      supportedOs: new Set([OperatingSystem.LINUX, OperatingSystem.WINDOWS]),
    });
    const {harness} = await createComponent(artifactDescriptor);

    expect(await harness.getSupportedOss()).toContain('Linux');
    expect(await harness.getSupportedOss()).toContain('Windows');
  });

  it('displays the artifact documentation', async () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'Test Artifact',
      doc: 'Test documentation',
    });
    const {harness} = await createComponent(artifactDescriptor);

    expect(await harness.getDocumentation()).toContain('Test documentation');
  });

  it('displays the artifact name', async () => {
    const artifactDescriptor = newArtifactDescriptor({
      name: 'Test Artifact',
    });
    const {harness} = await createComponent(artifactDescriptor);

    expect(await harness.getArtifactName()).toContain('Test Artifact');
  });
});
