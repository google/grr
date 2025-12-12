import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ForemanClientRuleType} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {ClientOsForm, ClientOsFormData} from './client_os_form';
import {ClientOsFormHarness} from './testing/client_os_form_harness';

initTestEnvironment();

async function createComponent(data: ClientOsFormData) {
  const fixture = TestBed.createComponent(ClientOsForm);
  fixture.componentRef.setInput('osData', data);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientOsFormHarness,
  );

  return {fixture, harness};
}

describe('Client Os Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ClientOsForm, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const data = new ClientOsFormData({});
    const {fixture} = await createComponent(data);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows initial values in the form', async () => {
    const data = new ClientOsFormData({
      osWindows: true,
      osDarwin: false,
      osLinux: true,
    });
    const {harness} = await createComponent(data);

    expect(await (await harness.windowsCheckbox()).isChecked()).toBeTrue();
    expect(await (await harness.darwinCheckbox()).isChecked()).toBeFalse();
    expect(await (await harness.linuxCheckbox()).isChecked()).toBeTrue();
  });

  it('shows error when no OS is selected', async () => {
    const data = new ClientOsFormData({
      osWindows: false,
      osDarwin: false,
      osLinux: false,
    });
    const {harness} = await createComponent(data);

    expect(await harness.getErrorText()).toEqual(
      'No clients will match, select at least one OS.',
    );
  });

  it('returns form data', async () => {
    const data = new ClientOsFormData({});
    const {fixture, harness} = await createComponent(data);

    await (await harness.windowsCheckbox()).check();
    await (await harness.linuxCheckbox()).check();

    expect(fixture.componentInstance.osData().getFormData()).toEqual({
      ruleType: ForemanClientRuleType.OS,
      os: {
        osWindows: true,
        osDarwin: false,
        osLinux: true,
      },
    });
  });
});
