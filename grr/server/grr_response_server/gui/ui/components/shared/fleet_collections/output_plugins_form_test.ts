import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  OutputPlugin,
  OutputPluginType,
} from '../../../lib/models/output_plugin';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {OutputPluginsForm} from './output_plugins_form';
import {OutputPluginsFormHarness} from './testing/output_plugins_form_harness';

initTestEnvironment();

async function createComponent(
  initialOutputPlugins: OutputPlugin[] = [],
  disabled = false,
) {
  const fixture = TestBed.createComponent(OutputPluginsForm);
  fixture.componentRef.setInput('initialOutputPlugins', initialOutputPlugins);
  fixture.componentRef.setInput('disabled', disabled);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OutputPluginsFormHarness,
  );

  return {fixture, harness};
}

describe('Output Plugin Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [OutputPluginsForm, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows supported and not supported plugins in the menu', fakeAsync(async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
      {
        pluginType: OutputPluginType.UNKNOWN,
        friendlyName: 'Unknown Output Plugin',
        description: '',
      },
    ]);
    const {harness} = await createComponent();

    const addPluginMenu = await harness.addPluginMenu();
    await addPluginMenu.open();
    const items = await addPluginMenu.getItems();
    expect(items.length).toBe(2);
    expect(await items[0].getText()).toBe('Email Output Plugin');
    expect(await items[0].isDisabled()).toBeFalse();
    expect(await items[1].getText()).toBe(
      'Unknown Output Plugin - not supported in the UI',
    );
    expect(await items[1].isDisabled()).toBeTrue();
  }));

  it('can initialize the form state', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    const {harness} = await createComponent([
      {
        pluginType: OutputPluginType.EMAIL,
        args: {
          'emailAddress': 'test@example.com',
        },
      },
    ]);

    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms).toHaveSize(1);
    const emailOutputPluginForm = emailOutputPluginForms[0];
    const emailInput = await emailOutputPluginForm.emailInput();
    expect(await emailInput.getValue()).toBe('test@example.com');
  });

  it('adds a new plugin when the menu item is clicked', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    const {harness} = await createComponent();

    const addPluginMenu = await harness.addPluginMenu();
    await addPluginMenu.open();
    const items = await addPluginMenu.getItems();
    await items[0].click();

    const pluginForms = await harness.pluginForms();
    expect(pluginForms.length).toBe(1);
    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms.length).toBe(1);
  });

  it('removes a plugin when the button is clicked', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    // Add a plugin to the form.
    const {harness} = await createComponent();
    const addPluginMenu = await harness.addPluginMenu();
    await addPluginMenu.open();
    const items = await addPluginMenu.getItems();
    await items[0].click();

    // Remove the plugin from the form.
    const removePluginButton = await harness.removePluginButton(0);
    await removePluginButton.click();

    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms.length).toBe(0);
  });

  it('disables the form state when disabled', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    const {harness} = await createComponent(
      [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            'emailAddress': 'test@example.com',
          },
        },
      ],
      true,
    );

    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms).toHaveSize(1);
    const emailOutputPluginForm = emailOutputPluginForms[0];
    const emailInput = await emailOutputPluginForm.emailInput();
    expect(await emailInput.getValue()).toBe('test@example.com');

    expect(await harness.isDisabled()).toBeTrue();
  });

  it('hides not supported plugins in the form when not disabled', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      // Email output plugin is not supported.
    ]);
    const {harness} = await createComponent(
      [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            'emailAddress': 'test@example.com',
          },
        },
      ],
      false,
    );

    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms).toHaveSize(0);
  });

  it('shows not supported plugins in the form when disabled', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      // Email output plugin is not supported.
    ]);
    const {harness} = await createComponent(
      [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            'emailAddress': 'test@example.com',
          },
        },
      ],
      true,
    );

    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    expect(emailOutputPluginForms).toHaveSize(1);
  });

  it('can build the form state', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    const {harness, fixture} = await createComponent([]);

    const addPluginMenu = await harness.addPluginMenu();
    await addPluginMenu.open();
    const items = await addPluginMenu.getItems();
    await items[0].click();
    const emailOutputPluginForms = await harness.emailOutputPluginForms();
    const emailOutputPluginForm = emailOutputPluginForms[0];
    const emailInput = await emailOutputPluginForm.emailInput();
    await emailInput.setValue('test@example.com');

    const plugins = fixture.componentInstance.getFormState();

    expect(plugins.length).toBe(1);
    expect(plugins[0].pluginType).toBe(OutputPluginType.EMAIL);
    expect(plugins[0].args).toEqual({
      emailAddress: 'test@example.com',
    });
  });
});
