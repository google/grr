import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {ArtifactDescriptor} from '../../lib/models/flow';
import {newArtifactDescriptor} from '../../lib/models/model_test_util';
import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {ADMINISTRATION_ROUTES} from '../app/routing';
import {ArtifactsAdministration} from './artifacts_administration';
import {CreateArtifactDialog} from './create_artifact_dialog';
import {ArtifactsAdministrationHarness} from './testing/artifacts_administration_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ArtifactsAdministration);

  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ArtifactsAdministrationHarness,
  );
  return {fixture, harness};
}

describe('Artifacts Administration Component', () => {
  let globalStoreMock: GlobalStoreMock;
  let mockDialog: jasmine.SpyObj<MatDialog>;
  let router: Router;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();
    mockDialog = jasmine.createSpyObj<MatDialog>(['open']);

    TestBed.configureTestingModule({
      imports: [
        ArtifactsAdministration,
        NoopAnimationsModule,
        RouterModule.forRoot(ADMINISTRATION_ROUTES),
      ],
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

    router = TestBed.inject(Router);
  }));

  it('is created', async () => {
    const {harness} = await createComponent();

    expect(harness).toBeDefined();
  });

  it('displays artifacts list', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({
        name: 'artifact1',
      }),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({
        name: 'artifact2',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );

    const {harness} = await createComponent();
    const artifactList = await harness.artifactList();
    const artifactListItems = await artifactList!.getItems();
    expect(artifactListItems.length).toBe(2);
    expect(await artifactListItems[0].getFullText()).toContain('artifact1');
    expect(await artifactListItems[1].getFullText()).toContain('artifact2');
  });

  it('navigates to artifact when clicking on artifact list item', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({
        name: 'artifact1',
      }),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({
        name: 'artifact2',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );
    const {harness} = await createComponent();

    const artifactList = await harness.artifactList();
    const artifactListItems = await artifactList!.getItems();
    await artifactListItems[0].click();

    expect(router.url).toBe('/administration/artifacts/artifact1');
  });

  it('filters artifacts list by name', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({
        name: 'artifact1',
      }),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({
        name: 'artifact2',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );
    const {harness} = await createComponent();
    const searchFormControl = await harness.searchFormControl();
    await searchFormControl.setValue('artifact1');

    const artifactList = await harness.artifactList();
    const artifactListItems = await artifactList!.getItems();
    expect(artifactListItems.length).toBe(1);
    expect(await artifactListItems[0].getFullText()).toContain('artifact1');
  });

  it('opens the create artifact dialog when "Create new artifact" button is clicked', async () => {
    const {harness} = await createComponent();

    const createArtifactButton = await harness.createArtifactButton();
    await createArtifactButton.click();

    const expectedDialogConfig = new MatDialogConfig();
    expectedDialogConfig.minWidth = '60vw';
    expectedDialogConfig.height = '70vh';
    expectedDialogConfig.autoFocus = false;

    expect(mockDialog.open).toHaveBeenCalledWith(
      CreateArtifactDialog,
      expectedDialogConfig,
    );
  });
});
