import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';

import {newArtifactDescriptor} from '../../lib/models/model_test_util';
import {initTestEnvironment} from '../../testing';
import {
  DeleteArtifactDialog,
  DeleteArtifactDialogData,
} from './delete_artifact_dialog';
import {DeleteArtifactDialogHarness} from './testing/delete_artifact_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: DeleteArtifactDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    DeleteArtifactDialog,
    DeleteArtifactDialogData
  >(DeleteArtifactDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.detectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(DeleteArtifactDialogHarness);
  return {fixture, dialogHarness};
}

describe('Delete Artifact Dialog', () => {
  const onDeleteArtifactSpy = jasmine.createSpy('onDeleteArtifact');

  beforeEach(waitForAsync(() => {
    onDeleteArtifactSpy.calls.reset();
    TestBed.configureTestingModule({
      declarations: [],
      imports: [DeleteArtifactDialog, MatTestDialogOpenerModule],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            artifact: newArtifactDescriptor({name: 'artifact_to_delete'}),
            onDeleteArtifact: onDeleteArtifactSpy,
          },
        },
      ],
    }).compileComponents();
  }));

  it('can be cancelled', async () => {
    const {fixture, dialogHarness} = await createDialog({
      artifact: newArtifactDescriptor({name: 'artifact_to_delete'}),
      onDeleteArtifact: onDeleteArtifactSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    await dialogHarness.clickCancelButton();
    expect(onDeleteArtifactSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.closedResult).toBeFalse();
  });

  it('calls `onDeleteArtifact` when "Delete" button is clicked', async () => {
    const {fixture, dialogHarness} = await createDialog({
      artifact: newArtifactDescriptor({name: 'artifact_to_delete'}),
      onDeleteArtifact: onDeleteArtifactSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    const title = await dialogHarness.getTitleText();
    expect(title).toContain('artifact_to_delete');

    await dialogHarness.clickDeleteButton();
    expect(onDeleteArtifactSpy).toHaveBeenCalledWith();

    expect(fixture.componentInstance.closedResult).toBeTrue();
  });
});
