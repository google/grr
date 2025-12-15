import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';

import {ClientLabel} from '../../lib/models/client';
import {newClientLabel} from '../../lib/models/model_test_util';
import {GlobalStore} from '../../store/global_store';
import {newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {
  ClientAddLabelDialog,
  ClientAddLabelDialogData,
} from './client_add_label_dialog';
import {ClientAddLabelDialogHarness} from './testing/client_add_label_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: ClientAddLabelDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    ClientAddLabelDialog,
    ClientAddLabelDialogData
  >(ClientAddLabelDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.autoDetectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(ClientAddLabelDialogHarness);
  return {fixture, dialogHarness};
}

describe('Client Add Label Dialog', () => {
  const clientLabels: readonly ClientLabel[] = [
    {owner: '', name: 'test_label'},
    {owner: '', name: 'another_label'},
  ];
  const allLabels = [
    'test_label',
    'another_label',
    'test_label_unset',
    'another_label_unset',
  ];
  const onAddLabelSpy = jasmine.createSpy('onAddLabel');

  beforeEach(waitForAsync(() => {
    onAddLabelSpy.calls.reset();
    TestBed.configureTestingModule({
      declarations: [],
      imports: [
        ClientAddLabelDialog,
        ReactiveFormsModule,
        MatTestDialogOpenerModule,
      ],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            clientLabels,
            allLabels,
            onAddLabel: onAddLabelSpy,
          },
        },
        {provide: GlobalStore, useValue: newGlobalStoreMock()},
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('can be cancelled', fakeAsync(async () => {
    const {fixture, dialogHarness} = await createDialog({
      clientLabels: [],
      allLabels: [],
      onAddLabel: onAddLabelSpy,
    });
    tick();
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    await dialogHarness.clickCancelButton();
    expect(onAddLabelSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.closedResult).toBeFalse();
  }));

  it('calls `onAddLabel` with the added label when "Add" button is clicked', fakeAsync(async () => {
    const {fixture, dialogHarness} = await createDialog({
      clientLabels: [],
      allLabels: [],
      onAddLabel: onAddLabelSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    await dialogHarness.setInput('newlabel');
    await dialogHarness.clickAddButton();

    expect(onAddLabelSpy).toHaveBeenCalledWith('newlabel');
    expect(fixture.componentInstance.closedResult).toBeTrue();
  }));

  it("doesn't allow adding the same label again", fakeAsync(async () => {
    const {fixture, dialogHarness} = await createDialog({
      clientLabels: [newClientLabel({name: 'test_label'})],
      allLabels: ['test_label'],
      onAddLabel: onAddLabelSpy,
    });
    await dialogHarness.setInput('test_label');

    expect(await dialogHarness.isAddButtonDisabled()).toBeTrue();

    await dialogHarness.clickAddButton();
    expect(onAddLabelSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.closedResult).toBeUndefined();
  }));

  it('updates suggested labels when input changes', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      clientLabels: [
        {owner: '', name: 'test_label'},
        {owner: '', name: 'another_label'},
      ],
      allLabels: [
        'test_label',
        'another_label',
        'test_label_unset',
        'another_label_unset',
      ],
      onAddLabel: onAddLabelSpy,
    });

    expect(await dialogHarness.getSuggestedLabels()).toEqual([
      'another_label_unset',
      'test_label_unset',
    ]);

    await dialogHarness.setInput('another');
    tick();
    expect(await dialogHarness.getSuggestedLabels()).toEqual([
      'another_label_unset',
    ]);
    await dialogHarness.setInput('label');
    tick();
    expect(await dialogHarness.getSuggestedLabels()).toEqual([
      'another_label_unset',
      'test_label_unset',
    ]);
    await dialogHarness.setInput('');
    tick();
    expect(await dialogHarness.getSuggestedLabels()).toEqual([
      'another_label_unset',
      'test_label_unset',
    ]);
  }));

  it('shows label already present option if the client has the label already', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      clientLabels: [{owner: '', name: 'test_label'}],
      allLabels: ['test_label'],
      onAddLabel: onAddLabelSpy,
    });

    await dialogHarness.setInput('test_label');
    tick();

    expect(await dialogHarness.getIsAlreadyPresentOptionVisible()).toBeTrue();
  }));

  it('shows "Add new label" option if the label is new', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      clientLabels: [],
      allLabels: ['test_label', 'another_label'],
      onAddLabel: onAddLabelSpy,
    });
    tick();
    expect(await dialogHarness.getIsNewLabelOptionVisible()).toBeFalse();
    await dialogHarness.setInput('test_label');
    tick();
    expect(await dialogHarness.getIsNewLabelOptionVisible()).toBeFalse();
    await dialogHarness.setInput('wohoo-new-label');
    tick();
    expect(await dialogHarness.getIsNewLabelOptionVisible()).toBeTrue();
    await dialogHarness.setInput('another_label');
    tick();
    expect(await dialogHarness.getIsNewLabelOptionVisible()).toBeFalse();
  }));
});
