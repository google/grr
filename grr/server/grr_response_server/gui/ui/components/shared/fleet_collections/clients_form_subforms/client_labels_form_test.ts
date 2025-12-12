import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleType,
  ForemanLabelClientRuleMatchMode,
} from '../../../../lib/api/api_interfaces';
import {GlobalStore} from '../../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../../store/store_test_util';
import {initTestEnvironment} from '../../../../testing';
import {ClientLabelsForm, ClientLabelsFormData} from './client_labels_form';
import {ClientLabelsFormHarness} from './testing/client_labels_form_harness';

initTestEnvironment();

async function createComponent(data: ClientLabelsFormData) {
  const fixture = TestBed.createComponent(ClientLabelsForm);
  fixture.componentRef.setInput('labelsData', data);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientLabelsFormHarness,
  );

  return {fixture, harness};
}

describe('Client Labels Form Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [ClientLabelsForm, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const data = new ClientLabelsFormData({}, () => {});
    const {fixture} = await createComponent(data);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows initial values in the form', async () => {
    const data = new ClientLabelsFormData(
      {
        labelNames: ['label1', 'label2'],
        matchMode: ForemanLabelClientRuleMatchMode.MATCH_ALL,
      },
      () => {},
    );
    const {harness} = await createComponent(data);

    expect(await harness.getLabelNames()).toEqual(['label1', 'label2']);
    expect(await harness.getMatchMode()).toEqual('Match all');
  });

  it('adds label names on button click', async () => {
    const data = new ClientLabelsFormData({}, () => {});
    const {harness} = await createComponent(data);

    await (await harness.addLabelButton()).click();
    await (await harness.addLabelButton()).click();

    expect(await harness.getLabelNames()).toEqual(['', '']);
  });

  it('removes label names on button click', async () => {
    const data = new ClientLabelsFormData(
      {
        labelNames: ['label1', 'label2'],
        matchMode: ForemanLabelClientRuleMatchMode.MATCH_ALL,
      },
      () => {},
    );
    const {harness} = await createComponent(data);

    await harness.removeLabel(0);

    expect(await harness.getLabelNames()).toEqual(['label2']);
  });

  it('shows autocomplete options', async () => {
    globalStoreMock.allLabels = signal(['label1', 'label2', 'label3']);
    const data = new ClientLabelsFormData({}, () => {});
    const {harness} = await createComponent(data);
    await (await harness.addLabelButton()).click();

    const autocompleteOptions = await harness.getLabelAutocompleteOptions(0);
    expect(autocompleteOptions).toEqual(['label1', 'label2', 'label3']);
  });

  it('returns form data', async () => {
    const data = new ClientLabelsFormData({}, () => {});
    const {fixture, harness} = await createComponent(data);

    await harness.setMatchMode('Match any');
    await (await harness.addLabelButton()).click();
    await harness.setLabel(0, 'label0');
    await (await harness.addLabelButton()).click();
    await harness.setLabel(1, 'label1');

    expect(fixture.componentInstance.labelsData().getFormData()).toEqual({
      ruleType: ForemanClientRuleType.LABEL,
      label: {
        labelNames: ['label0', 'label1'],
        matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY,
      },
    });
  });

  it('calls onChange callback when form data is changed', async () => {
    const onChange = jasmine.createSpy('onChange');
    const data = new ClientLabelsFormData({}, onChange);
    const {harness} = await createComponent(data);

    await harness.setMatchMode('Match any');
    await (await harness.addLabelButton()).click();
    await harness.setLabel(0, 'label0');

    // 4 times:
    // - initial call after creation
    // - after match mode change
    // - after label name added
    // - after label value changed
    expect(onChange).toHaveBeenCalledTimes(4);
  });
});
