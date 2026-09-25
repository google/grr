import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ArtifactDescriptor} from '../../lib/models/flow';
import {newArtifactDescriptor} from '../../lib/models/model_test_util';
import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {Artifact} from './artifact';
import {DeleteArtifactDialog} from './delete_artifact_dialog';
import {ArtifactHarness} from './testing/artifact_harness';

initTestEnvironment();

async function createComponent(artifactName?: string) {
  const fixture = TestBed.createComponent(Artifact);
  fixture.componentRef.setInput('artifactName', artifactName);
  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ArtifactHarness,
  );
  return {fixture, harness};
}

describe('Artifact Component', () => {
  let globalStoreMock: GlobalStoreMock;
  let mockDialog: jasmine.SpyObj<MatDialog>;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();
    mockDialog = jasmine.createSpyObj<MatDialog>(['open']);

    TestBed.configureTestingModule({
      imports: [Artifact, NoopAnimationsModule],
      providers: [
        {
          provide: MatDialog,
          useValue: mockDialog,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness} = await createComponent();

    expect(harness).toBeDefined();
  });

  it('shows artifact details for valid artifact name', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact',
      newArtifactDescriptor({
        name: 'artifact',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    const {harness} = await createComponent('artifact');

    expect(await harness.hasArtifactDetails()).toBeTrue();
  });

  it('does not show artifact details for invalid artifact name', async () => {
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>([]),
    );
    const {harness} = await createComponent('unknown_artifact');

    expect(await harness.hasArtifactDetails()).toBeFalse();
    expect(await harness.getNoArtifactDetails()).toBe(
      'Artifact unknown_artifact not found',
    );
  });

  it('does not show artifact details for undefined artifact name', async () => {
    const {harness} = await createComponent(/* missing artifactName */);

    expect(await harness.hasArtifactDetails()).toBeFalse();
    expect(await harness.getNoArtifactDetails()).toBe('No artifact selected');
  });

  it('shows delete button for custom artifact', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact',
      newArtifactDescriptor({
        name: 'artifact',
        isCustom: true,
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    const {harness} = await createComponent('artifact');

    expect(await harness.hasDeleteButton()).toBeTrue();
  });

  it('opens delete artifact dialog when delete button is clicked', async () => {
    const artifactToDelete = newArtifactDescriptor({
      name: 'artifact',
      isCustom: true,
    });
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set('artifact', artifactToDelete);
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    const {harness} = await createComponent('artifact');

    const deleteButton = await harness.deleteButton();
    await deleteButton!.click();

    const expectedDialogConfig = new MatDialogConfig();
    expectedDialogConfig.data = {
      artifact: artifactToDelete,
      onDeleteArtifact: jasmine.any(Function),
    };
    expect(mockDialog.open).toHaveBeenCalledWith(
      DeleteArtifactDialog,
      expectedDialogConfig,
    );
  });

  it('does not show delete button for non-custom artifact', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact',
      newArtifactDescriptor({
        name: 'artifact',
        isCustom: false,
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    const {harness} = await createComponent('artifact');

    expect(await harness.hasDeleteButton()).toBeFalse();
  });
});
