import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';

import {newClientLabel} from '../../lib/models/model_test_util';
import {initTestEnvironment} from '../../testing';
import {
  ClientRemoveLabelDialog,
  ClientRemoveLabelDialogData,
} from './client_remove_label_dialog';
import {ClientRemoveLabelDialogHarness} from './testing/client_remove_label_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: ClientRemoveLabelDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    ClientRemoveLabelDialog,
    ClientRemoveLabelDialogData
  >(ClientRemoveLabelDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.detectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(ClientRemoveLabelDialogHarness);
  return {fixture, dialogHarness};
}

describe('Client Remove Label Dialog', () => {
  const onRemoveLabelSpy = jasmine.createSpy('onRemoveLabel');

  beforeEach(waitForAsync(() => {
    onRemoveLabelSpy.calls.reset();
    TestBed.configureTestingModule({
      declarations: [],
      imports: [ClientRemoveLabelDialog, MatTestDialogOpenerModule],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            label: newClientLabel({name: 'label_to_remove'}),
            onRemoveLabel: onRemoveLabelSpy,
          },
        },
      ],
    }).compileComponents();
  }));

  it('can be cancelled', async () => {
    const {fixture, dialogHarness} = await createDialog({
      label: newClientLabel({name: 'label_to_remove'}),
      onRemoveLabel: onRemoveLabelSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    await dialogHarness.clickCancelButton();
    expect(onRemoveLabelSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.closedResult).toBeFalse();
  });

  it('calls `onRemoveLabel` when "Remove" button is clicked', async () => {
    const {fixture, dialogHarness} = await createDialog({
      label: newClientLabel({name: 'label_to_remove'}),
      onRemoveLabel: onRemoveLabelSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    const title = await dialogHarness.getTitleText();
    expect(title).toContain('label_to_remove');

    await dialogHarness.clickRemoveButton();
    expect(onRemoveLabelSpy).toHaveBeenCalledWith();

    expect(fixture.componentInstance.closedResult).toBeTrue();
  });
});
