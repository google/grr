import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {YaraProcessScanRequest} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {YaraProcessScanFormHarness} from './testing/yara_process_scan_form_harness';
import {FilterMode, YaraProcessScanForm} from './yara_process_scan_form';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(YaraProcessScanForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    YaraProcessScanFormHarness,
  );
  return {fixture, harness};
}

describe('Yara Process Scan Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [YaraProcessScanForm, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('triggers onSubmit callback when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('YaraProcessScan');
        expect(flowArgs).toEqual({
          yaraSignature: 'FOO BAR',
          processRegex: undefined,
          cmdlineRegex: undefined,
          pids: ['123', '456'],
          contextWindow: 100,
          skipReadonlyRegions: true,
          skipExecutableRegions: true,
          skipSpecialRegions: false,
          skipSharedRegions: false,
          skipMappedFiles: false,
        });
        onSubmitCalled = true;
      },
    );
    await harness.setYaraRule('FOO BAR');
    await harness.setFilterMode('PID');
    await harness.setPidFilter('123,456');
    await harness.setContextCaptureWindow(100);

    const skipReadonlyCheckbox = await harness.skipReadonlyCheckboxHarness();
    await skipReadonlyCheckbox.check();

    const skipExecutableCheckbox =
      await harness.skipExecutableCheckboxHarness();
    await skipExecutableCheckbox.check();

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      yaraSignature: 'rule foo { condition: true }',
      filterMode: FilterMode.PID,
      pids: [123, 456],
      processRegex: '',
      cmdlineRegex: '',
      contextWindow: 100,
      skipReadonlyRegions: true,
      skipExecutableRegions: true,
      skipSpecialRegions: true,
      skipSharedRegions: true,
      skipMappedFiles: true,
    });

    const expectedFlowArgs: YaraProcessScanRequest = {
      yaraSignature: 'rule foo { condition: true }',
      pids: ['123', '456'],
      processRegex: undefined,
      cmdlineRegex: undefined,
      contextWindow: 100,
      skipReadonlyRegions: true,
      skipExecutableRegions: true,
      skipSpecialRegions: true,
      skipSharedRegions: true,
      skipMappedFiles: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: YaraProcessScanRequest = {
      yaraSignature: 'rule foo { condition: true }',
      pids: undefined,
      processRegex: 'foo-**-bar',
      cmdlineRegex: undefined,
      contextWindow: 100,
      skipReadonlyRegions: true,
      skipExecutableRegions: true,
      skipSpecialRegions: true,
      skipSharedRegions: true,
      skipMappedFiles: true,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      yaraSignature: 'rule foo { condition: true }',
      filterMode: FilterMode.NAME,
      pids: [],
      processRegex: 'foo-**-bar',
      cmdlineRegex: '',
      contextWindow: 100,
      skipReadonlyRegions: true,
      skipExecutableRegions: true,
      skipSpecialRegions: true,
      skipSharedRegions: true,
      skipMappedFiles: true,
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness} = await createComponent({
      yaraSignature: 'rule foo { condition: true }',
      pids: [],
      processRegex: '',
      cmdlineRegex: 'foo-**-bar',
      contextWindow: 100,
      skipReadonlyRegions: false,
      skipExecutableRegions: false,
      skipSpecialRegions: true,
      skipSharedRegions: true,
      skipMappedFiles: true,
    });

    expect(await harness.getCmdlineFilter()).toBe('foo-**-bar');
    expect(await harness.getContextCaptureWindow()).toBe('100 B');
    const skipReadonlyCheckbox = await harness.skipReadonlyCheckboxHarness();
    expect(await skipReadonlyCheckbox.isChecked()).toBeFalse();
    const skipExecutableCheckbox =
      await harness.skipExecutableCheckboxHarness();
    expect(await skipExecutableCheckbox.isChecked()).toBeFalse();
    const skipSpecialCheckbox = await harness.skipSpecialCheckboxHarness();
    expect(await skipSpecialCheckbox.isChecked()).toBeTrue();
    const skipSharedCheckbox = await harness.skipSharedCheckboxHarness();
    expect(await skipSharedCheckbox.isChecked()).toBeTrue();
    const skipMappedFilesCheckbox =
      await harness.skipMappedFilesCheckboxHarness();
    expect(await skipMappedFilesCheckbox.isChecked()).toBeTrue();
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('shows a PID input field', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setFilterMode('PID');
    await harness.setPidFilter('123,456');

    expect(fixture.componentInstance.flowArgs()).toEqual(
      jasmine.objectContaining({
        pids: ['123', '456'],
      }),
    );
  });

  it('shows a process name input field', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setFilterMode('Name');
    await harness.setNameFilter('foo');

    expect(fixture.componentInstance.flowArgs()).toEqual(
      jasmine.objectContaining({
        processRegex: 'foo',
      }),
    );
  });

  it('shows a process cmdline input field', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setFilterMode('Cmdline');
    await harness.setCmdlineFilter('foo');

    expect(fixture.componentInstance.flowArgs()).toEqual(
      jasmine.objectContaining({
        cmdlineRegex: 'foo',
      }),
    );
  });

  it('shows a context window input field', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setContextCaptureWindow(999);

    expect(fixture.componentInstance.flowArgs()).toEqual(
      jasmine.objectContaining({
        contextWindow: 999,
      }),
    );
  });
});
