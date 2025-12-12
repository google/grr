import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {EmailOutputPluginArgs} from '../../../../lib/api/api_interfaces';
import {OutputPluginType} from '../../../../lib/models/output_plugin';
import {initTestEnvironment} from '../../../../testing';
import {OutputPluginData} from '../abstract_output_plugin_form_data';
import {
  EmailOutputPluginData,
  EmailOutputPluginForm,
} from './email_output_plugin_form';
import {EmailOutputPluginFormHarness} from './testing/email_output_plugin_form_harness';

initTestEnvironment();

async function createComponent(
  plugin: OutputPluginData<EmailOutputPluginArgs>,
) {
  const fixture = TestBed.createComponent(EmailOutputPluginForm);
  fixture.componentRef.setInput('plugin', plugin);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    EmailOutputPluginFormHarness,
  );

  return {fixture, harness};
}

describe('Email Output Plugin Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [EmailOutputPluginForm, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const plugin = new EmailOutputPluginData(undefined);
    const {fixture} = await createComponent(plugin);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('is created with email address', async () => {
    const plugin = new EmailOutputPluginData({
      'emailAddress': 'test@example.com',
    });
    const {harness} = await createComponent(plugin);

    const emailInput = await harness.emailInput();
    expect(await emailInput.getValue()).toBe('test@example.com');
  });

  it('updates the email address via the input', async () => {
    const plugin = new EmailOutputPluginData({
      'emailAddress': 'test@example.com',
    });
    const {harness} = await createComponent(plugin);

    const emailInput = await harness.emailInput();
    await emailInput.setValue('new@example.com');

    expect(await emailInput.getValue()).toBe('new@example.com');
  });

  it('returns the correct plugin', async () => {
    const data = new EmailOutputPluginData({
      'emailAddress': 'test@example.com',
    });
    await createComponent(data);

    const plugin = data.getPlugin();
    expect(plugin).toEqual({
      pluginType: OutputPluginType.EMAIL,
      args: {
        emailAddress: 'test@example.com',
      },
    });
  });
});
