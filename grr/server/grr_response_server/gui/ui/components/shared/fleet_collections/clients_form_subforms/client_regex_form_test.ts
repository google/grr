import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleType,
  ForemanRegexClientRuleForemanStringField,
} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {ClientRegexForm, ClientRegexFormData} from './client_regex_form';
import {ClientRegexFormHarness} from './testing/client_regex_form_harness';

initTestEnvironment();

async function createComponent(data: ClientRegexFormData) {
  const fixture = TestBed.createComponent(ClientRegexForm);
  fixture.componentRef.setInput('regexData', data);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientRegexFormHarness,
  );

  return {fixture, harness};
}

describe('Client Regex Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ClientRegexForm, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const data = new ClientRegexFormData({});
    const {fixture} = await createComponent(data);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows initial values in the form', async () => {
    const data = new ClientRegexFormData({
      attributeRegex: 'some*regex',
    });
    const {harness} = await createComponent(data);

    expect(await harness.getRegexInput()).toEqual('some*regex');
  });

  it('returns form data', async () => {
    const data = new ClientRegexFormData({
      field: ForemanRegexClientRuleForemanStringField.CLIENT_ID,
    });
    const {fixture, harness} = await createComponent(data);

    await harness.setRegexInput('some*regex');

    expect(fixture.componentInstance.regexData().getFormData()).toEqual({
      ruleType: ForemanClientRuleType.REGEX,
      regex: {
        attributeRegex: 'some*regex',
        field: ForemanRegexClientRuleForemanStringField.CLIENT_ID,
      },
    });
  });
});
