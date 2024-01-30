import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {getInputValue} from '../../../../form_testing';
import {newOutputPluginDescriptor} from '../../../../lib/models/model_test_util';
import {OutputPluginDescriptorMap} from '../../../../lib/models/output_plugin';
import {ConfigGlobalStore} from '../../../../store/config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from '../../../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../../../testing';

import {OutputPluginsFormModule} from './module';
import {OutputPluginsForm, PluginType} from './output_plugins_form';

initTestEnvironment();

describe('output plugins form test', () => {
  let configGlobalStoreMock: ConfigGlobalStoreMock;
  beforeEach(waitForAsync(() => {
    configGlobalStoreMock = mockConfigGlobalStore();
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, OutputPluginsFormModule],
      providers: [
        {
          provide: ConfigGlobalStore,
          useFactory: () => configGlobalStoreMock,
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    const button = fixture.debugElement.query(
      By.css('#output-plugins-form-toggle'),
    );
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();
  });

  it('opens contents on click on header', () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    const header = fixture.debugElement.query(By.css('.header'));
    header.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('builds correct OutputPluginDescriptor using the form values', async () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    // TODO: Choose on selection box instead.
    fixture.componentInstance.addNewPlugin(PluginType.BIGQUERY);
    fixture.detectChanges();

    const annotationInput = await loader.getHarness(MatInputHarness);
    await annotationInput.setValue('test');
    fixture.detectChanges();

    expect(await getInputValue(fixture, '#plugin_0_annotation_0')).toEqual(
      'test',
    );
  });

  it('setFormState updates annotation input field', async () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    const args = {exportOptions: {annotations: ['lalala', 'lelele']}};
    fixture.componentInstance.setFormState([
      {
        pluginName: 'BigQueryOutputPlugin',
        args,
      },
    ]);
    fixture.detectChanges();

    expect(await getInputValue(fixture, '#plugin_0_annotation_0')).toEqual(
      'lalala',
    );
    expect(await getInputValue(fixture, '#plugin_0_annotation_1')).toEqual(
      'lelele',
    );
  });

  it('adds annotation control', async () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    // TODO: Choose on selection box instead.
    fixture.componentInstance.addNewPlugin(PluginType.BIGQUERY);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('#plugin_0_annotation_0')),
    ).toBeTruthy();
    expect(fixture.componentInstance.annotations(0).length).toBe(1);

    const addAnnotation = fixture.debugElement.query(By.css('#add-annotation'));
    addAnnotation.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('#plugin_0_annotation_1')),
    ).toBeTruthy();
    expect(fixture.componentInstance.annotations(0).length).toBe(2);
  });

  it('removes annotation control', async () => {
    const fixture = TestBed.createComponent(OutputPluginsForm);
    // TODO: Choose on selection box instead.
    fixture.componentInstance.addNewPlugin(PluginType.BIGQUERY);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('#plugin_0_annotation_0')),
    ).toBeTruthy();
    expect(fixture.componentInstance.plugins.length).toBe(1);
    expect(fixture.componentInstance.annotations(0).length).toBe(1);

    const removeAnnotation = fixture.debugElement.query(
      By.css('#remove_plugin_0'),
    );
    removeAnnotation.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('#plugin_0_annotation_0')),
    ).toBeFalsy();
    expect(fixture.componentInstance.plugins.length).toBe(0);
  });
});
