import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';

import {newSafetyLimits} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';
import {
  ModifyFleetCollectionDialog,
  ModifyFleetCollectionDialogData,
} from './modify_fleet_collection_dialog';
import {ModifyFleetCollectionDialogHarness} from './testing/modify_fleet_collection_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: ModifyFleetCollectionDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    ModifyFleetCollectionDialog,
    ModifyFleetCollectionDialogData
  >(ModifyFleetCollectionDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.detectChanges();

  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(
    ModifyFleetCollectionDialogHarness,
  );
  return {fixture, dialogHarness};
}

describe('Modify Fleet Collection Dialog', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ModifyFleetCollectionDialog, MatTestDialogOpenerModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createDialog({
      currentSafetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 567,
      }),
      onSubmit: (clientLimit, clientRate) => {},
    });

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('initializes with correct values', async () => {
    const {dialogHarness} = await createDialog({
      currentSafetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 567,
      }),
      onSubmit: (clientLimit, clientRate) => {},
    });

    const rolloutForm = await dialogHarness.rolloutForm();
    const clientLimitInput = await rolloutForm.getClientLimitInput();
    expect(await clientLimitInput.getValue()).toBe('1234');
    const clientRateInput = await rolloutForm.getRolloutSpeedInput();
    expect(await clientRateInput.getValue()).toBe('567');
  });

  it('calls the submit function when clicking on the submit button', async () => {
    const onSubmitSpy = jasmine.createSpy('onSubmit');
    const {dialogHarness} = await createDialog({
      currentSafetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 567,
      }),
      onSubmit: onSubmitSpy,
    });

    const submitButton = await dialogHarness.submitButton();
    await submitButton.click();

    expect(onSubmitSpy).toHaveBeenCalledWith(BigInt(1234), 567);
  });

  it('does not call the submit function when clicking on the cancel button', async () => {
    const onSubmitSpy = jasmine.createSpy('onSubmit');
    const {dialogHarness} = await createDialog({
      currentSafetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 567,
      }),
      onSubmit: onSubmitSpy,
    });

    const cancelButton = await dialogHarness.cancelButton();
    await cancelButton.click();

    expect(onSubmitSpy).not.toHaveBeenCalled();
  });
});
