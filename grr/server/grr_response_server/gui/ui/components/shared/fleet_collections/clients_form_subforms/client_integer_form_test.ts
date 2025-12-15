import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleType,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {ClientIntegerForm, ClientIntegerFormData} from './client_integer_form';
import {ClientIntegerFormHarness} from './testing/client_integer_form_harness';

initTestEnvironment();

async function createComponent(data: ClientIntegerFormData) {
  const fixture = TestBed.createComponent(ClientIntegerForm);
  fixture.componentRef.setInput('integerData', data);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientIntegerFormHarness,
  );

  return {fixture, harness};
}

describe('Client Integer Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ClientIntegerForm, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const data = new ClientIntegerFormData({});
    const {fixture} = await createComponent(data);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows initial values in the form', async () => {
    const data = new ClientIntegerFormData({
      operator: ForemanIntegerClientRuleOperator.EQUAL,
      value: '1337',
    });
    const {harness} = await createComponent(data);

    expect(await (await harness.operatorSelect()).getValueText()).toBe('Equal');
    expect(await (await harness.valueInput()).getValue()).toBe('1337');
  });

  it('returns form data', async () => {
    const data = new ClientIntegerFormData({
      field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
    });
    const {fixture, harness} = await createComponent(data);

    await (await harness.operatorSelect()).clickOptions({text: 'Less Than'});
    await (await harness.valueInput()).setValue('1337');

    expect(fixture.componentInstance.integerData().getFormData()).toEqual({
      ruleType: ForemanClientRuleType.INTEGER,
      integer: {
        operator: ForemanIntegerClientRuleOperator.LESS_THAN,
        value: '1337',
        field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
      },
    });
  });
});
