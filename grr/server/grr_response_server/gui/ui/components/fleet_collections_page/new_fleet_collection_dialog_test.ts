import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {initTestEnvironment} from '../../testing';
import {FLEET_COLLECTION_ROUTES} from '../app/routing';
import {NewFleetCollectionDialog} from './new_fleet_collection_dialog';
import {NewFleetCollectionDialogHarness} from './testing/new_fleet_collection_dialog_harness';

initTestEnvironment();

async function createDialog() {
  const opener = MatTestDialogOpener.withComponent(NewFleetCollectionDialog);

  const fixture = TestBed.createComponent(opener);
  fixture.autoDetectChanges();

  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(
    NewFleetCollectionDialogHarness,
  );
  return {fixture, dialogHarness};
}

describe('New Fleet Collection Dialog', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [],
      imports: [
        MatTestDialogOpenerModule,
        NewFleetCollectionDialog,
        NoopAnimationsModule,
        RouterModule.forRoot(FLEET_COLLECTION_ROUTES),
      ],
      providers: [],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createDialog();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('can be cancelled', async () => {
    const {fixture, dialogHarness} = await createDialog();

    const cancelButton = await dialogHarness.cancelButton();
    await cancelButton.click();

    expect(fixture.componentInstance.closedResult).toBeFalse();
    const location = TestBed.inject(Location);
    expect(location.path()).not.toContain('/new-fleet-collections');
  });

  it('enables Next button when client ID and flow ID are provided', async () => {
    const {dialogHarness} = await createDialog();

    const clientIdInput = await dialogHarness.clientIdInput();
    await clientIdInput.setValue('C.1234567890abcdef');

    const flowIdInput = await dialogHarness.flowIdInput();
    await flowIdInput.setValue('1234567890ABCDEF');

    const createFromFlowButton = await dialogHarness.createFromFlowButton();
    expect(await createFromFlowButton.isDisabled()).toBeFalse();
  });

  it('disables Next button when no client ID is provided', async () => {
    const {dialogHarness} = await createDialog();

    const clientIdInput = await dialogHarness.clientIdInput();
    await clientIdInput.setValue('');

    const flowIdInput = await dialogHarness.flowIdInput();
    await flowIdInput.setValue('1234567890ABCDEF');

    const createFromFlowButton = await dialogHarness.createFromFlowButton();
    expect(await createFromFlowButton.isDisabled()).toBeTrue();
  });

  it('disables Next button when no flow ID is provided', async () => {
    const {dialogHarness} = await createDialog();

    const clientIdInput = await dialogHarness.clientIdInput();
    await clientIdInput.setValue('C.1234567890abcdef');

    const flowIdInput = await dialogHarness.flowIdInput();
    await flowIdInput.setValue('');

    const createFromFlowButton = await dialogHarness.createFromFlowButton();
    expect(await createFromFlowButton.isDisabled()).toBeTrue();
  });

  it('enables Next button when fleet collection ID is provided', async () => {
    const {dialogHarness} = await createDialog();

    const fleetCollectionIdInput = await dialogHarness.fleetCollectionIdInput();
    await fleetCollectionIdInput.setValue('1234567890ABCDEF');

    const createFromFleetCollectionButton =
      await dialogHarness.createFromFleetCollectionButton();
    expect(await createFromFleetCollectionButton.isDisabled()).toBeFalse();
  });

  it('disables Next button when no fleet collection ID is provided', async () => {
    const {dialogHarness} = await createDialog();

    const fleetCollectionIdInput = await dialogHarness.fleetCollectionIdInput();
    await fleetCollectionIdInput.setValue('');

    const createFromFleetCollectionButton =
      await dialogHarness.createFromFleetCollectionButton();
    expect(await createFromFleetCollectionButton.isDisabled()).toBeTrue();
  });

  it('navigates to the fleet collections page with client ID and flow ID when Next is clicked', fakeAsync(async () => {
    const location = TestBed.inject(Location);
    const {dialogHarness} = await createDialog();

    const clientIdInput = await dialogHarness.clientIdInput();
    await clientIdInput.setValue('C.1234567890abcdef');

    const flowIdInput = await dialogHarness.flowIdInput();
    await flowIdInput.setValue('1234567890ABCDEF');

    const createFromFlowButton = await dialogHarness.createFromFlowButton();
    await createFromFlowButton.click();

    expect(location.path()).toEqual(
      '/new-fleet-collection?clientId=C.1234567890abcdef&flowId=1234567890ABCDEF',
    );
  }));

  it('navigates to the fleet collections page with fleet collection ID when Next is clicked', fakeAsync(async () => {
    const location = TestBed.inject(Location);
    const {dialogHarness} = await createDialog();

    const fleetCollectionIdInput = await dialogHarness.fleetCollectionIdInput();
    await fleetCollectionIdInput.setValue('1234567890ABCDEF');

    const createFromFleetCollectionButton =
      await dialogHarness.createFromFleetCollectionButton();
    await createFromFleetCollectionButton.click();

    expect(location.path()).toEqual(
      '/new-fleet-collection?fleetCollectionId=1234567890ABCDEF',
    );
  }));
});
