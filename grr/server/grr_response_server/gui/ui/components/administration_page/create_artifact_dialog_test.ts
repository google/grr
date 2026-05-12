import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {CreateArtifactDialog} from './create_artifact_dialog';
import {CreateArtifactDialogHarness} from './testing/create_artifact_dialog_harness';

initTestEnvironment();

async function createDialog() {
  const opener =
    MatTestDialogOpener.withComponent<CreateArtifactDialog>(
      CreateArtifactDialog,
    );

  const fixture = TestBed.createComponent(opener);
  fixture.autoDetectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(CreateArtifactDialogHarness);
  return {fixture, dialogHarness};
}

describe('Create Artifact Dialog', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      declarations: [],
      imports: [
        CreateArtifactDialog,
        ReactiveFormsModule,
        MatTestDialogOpenerModule,
      ],
      providers: [{provide: GlobalStore, useValue: globalStoreMock}],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createDialog();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('can be cancelled', fakeAsync(async () => {
    const {dialogHarness} = await createDialog();

    const cancelButton = await dialogHarness.cancelButton();
    await cancelButton.click();

    expect(globalStoreMock.uploadArtifact).not.toHaveBeenCalled();
  }));

  it('calls `uploadArtifact` with the artifact definition when "Create" button is clicked', fakeAsync(async () => {
    const {dialogHarness} = await createDialog();

    const artifactFormField = await dialogHarness.artifactFormField();
    const artifactInput =
      (await artifactFormField.getControl()) as MatInputHarness;
    await artifactInput!.setValue('test_artifact');
    const createButton = await dialogHarness.createButton();
    await createButton.click();

    expect(globalStoreMock.uploadArtifact).toHaveBeenCalledWith(
      'test_artifact',
    );
  }));

  it('disables "Create" button when artifact definition is empty', fakeAsync(async () => {
    const {dialogHarness} = await createDialog();

    const createButton = await dialogHarness.createButton();
    expect(await createButton.isDisabled()).toBeTrue();
  }));
});
