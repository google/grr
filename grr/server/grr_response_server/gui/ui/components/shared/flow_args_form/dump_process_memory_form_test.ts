import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {YaraProcessDumpArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {DumpProcessMemoryForm, FilterMode} from './dump_process_memory_form';
import {DumpProcessMemoryFormHarness} from './testing/dump_process_memory_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(DumpProcessMemoryForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    DumpProcessMemoryFormHarness,
  );
  return {fixture, harness};
}

describe('Dump Process Memory Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [DumpProcessMemoryForm, NoopAnimationsModule],
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
        expect(flowName).toBe('DumpProcessMemory');
        expect(flowArgs).toEqual({
          pids: ['123', '456'],
          processRegex: undefined,
          dumpAllProcesses: false,

          skipSpecialRegions: true,
          skipMappedFiles: true,
          skipSharedRegions: true,
          skipExecutableRegions: true,
          skipReadonlyRegions: true,
        });
        onSubmitCalled = true;
      },
    );
    await harness.setFilterMode('PID');
    const pidsInput = await harness.getPidInputHarness();
    await pidsInput?.setValue('123, 456');

    const skipSpecialRegions = await harness.skipSpecialRegionsCheckbox();
    await skipSpecialRegions.check();

    const skipMappedFiles = await harness.skipMappedFilesCheckbox();
    await skipMappedFiles.check();

    const skipSharedRegions = await harness.skipSharedRegionsCheckbox();
    await skipSharedRegions.check();

    const skipExecutableRegions = await harness.skipExecutableRegionsCheckbox();
    await skipExecutableRegions.check();

    const skipReadonlyRegions = await harness.skipReadonlyRegionsCheckbox();
    await skipReadonlyRegions.check();

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args if filter mode is PID', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      filterMode: FilterMode.PID,
      pids: [123, 456],
      dumpAllProcesses: false,
      processRegex: '',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });

    const expectedFlowArgs: YaraProcessDumpArgs = {
      pids: ['123', '456'],
      processRegex: undefined,
      dumpAllProcesses: false,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the form state to flow args if filter mode is NAME', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      filterMode: FilterMode.NAME,
      pids: [],
      dumpAllProcesses: false,
      processRegex: 'python\\d?',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });

    const expectedFlowArgs: YaraProcessDumpArgs = {
      pids: undefined,
      processRegex: 'python\\d?',
      dumpAllProcesses: false,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the form state to flow args if filter mode is ALL', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      filterMode: FilterMode.ALL,
      pids: [],
      dumpAllProcesses: false,
      processRegex: '',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });

    const expectedFlowArgs: YaraProcessDumpArgs = {
      pids: undefined,
      processRegex: undefined,
      dumpAllProcesses: true,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state if filter mode is PID', async () => {
    const {fixture} = await createComponent();
    const flowArgs: YaraProcessDumpArgs = {
      pids: ['123', '456'],
      processRegex: undefined,
      dumpAllProcesses: false,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      filterMode: FilterMode.PID,
      pids: [123, 456],
      dumpAllProcesses: false,
      processRegex: '',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });
  });

  it('converts the flow args to form state if filter mode is NAME', async () => {
    const {fixture} = await createComponent();
    const flowArgs: YaraProcessDumpArgs = {
      pids: undefined,
      processRegex: 'python\\d?',
      dumpAllProcesses: false,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      filterMode: FilterMode.NAME,
      pids: [],
      dumpAllProcesses: false,
      processRegex: 'python\\d?',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });
  });

  it('converts the flow args to form state if filter mode is ALL', async () => {
    const {fixture} = await createComponent();
    const flowArgs: YaraProcessDumpArgs = {
      pids: undefined,
      processRegex: undefined,
      dumpAllProcesses: true,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      filterMode: FilterMode.ALL,
      pids: [],
      dumpAllProcesses: true,
      processRegex: '',
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });
  });

  it('resets the flow args when passing flowArgs', fakeAsync(async () => {
    const {harness} = await createComponent({
      pids: undefined,
      processRegex: 'python\\d?',
      dumpAllProcesses: false,
      skipSpecialRegions: true,
      skipMappedFiles: false,
      skipSharedRegions: true,
      skipExecutableRegions: false,
      skipReadonlyRegions: true,
    });
    tick();
    expect(await harness.getFilterMode()).toBe('Name');
    const regexInput = await harness.getRegexInputHarness();
    expect(await regexInput.getValue()).toBe('python\\d?');
    const skipSpecialRegions = await harness.skipSpecialRegionsCheckbox();
    expect(await skipSpecialRegions.isChecked()).toBeTrue();
    const skipMappedFiles = await harness.skipMappedFilesCheckbox();
    expect(await skipMappedFiles.isChecked()).toBeFalse();
    const skipSharedRegions = await harness.skipSharedRegionsCheckbox();
    expect(await skipSharedRegions.isChecked()).toBeTrue();
    const skipExecutableRegions = await harness.skipExecutableRegionsCheckbox();
    expect(await skipExecutableRegions.isChecked()).toBeFalse();
    const skipReadonlyRegions = await harness.skipReadonlyRegionsCheckbox();
    expect(await skipReadonlyRegions.isChecked()).toBeTrue();
  }));

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('initializes the filter mode to PID and skips no memory regions', async () => {
    const {harness} = await createComponent();
    expect(await harness.getFilterMode()).toBe('PID');

    const skipReadonlyRegions = await harness.skipReadonlyRegionsCheckbox();
    expect(await skipReadonlyRegions.isChecked()).toBeFalse();
    const skipExecutableRegions = await harness.skipExecutableRegionsCheckbox();
    expect(await skipExecutableRegions.isChecked()).toBeFalse();
    const skipSpecialRegions = await harness.skipSpecialRegionsCheckbox();
    expect(await skipSpecialRegions.isChecked()).toBeFalse();
    const skipSharedRegions = await harness.skipSharedRegionsCheckbox();
    expect(await skipSharedRegions.isChecked()).toBeFalse();
    const skipMappedFiles = await harness.skipMappedFilesCheckbox();
    expect(await skipMappedFiles.isChecked()).toBeFalse();
  });

  it('input is disabled when filter mode is ALL', async () => {
    const {harness} = await createComponent();
    await harness.setFilterMode('All');
    const allInput = await harness.getAllInputHarness();
    expect(await allInput.isDisabled()).toBeTrue();
  });

  it('toggling the filter mode updates the input harnesses', async () => {
    const {harness} = await createComponent();
    expect(await harness.getFilterMode()).toBe('PID');
    expect(await harness.hasPidInputHarness()).toBeTrue();
    expect(await harness.hasRegexInputHarness()).toBeFalse();

    await harness.setFilterMode('Name');
    expect(await harness.hasRegexInputHarness()).toBeTrue();
    expect(await harness.hasAllInputHarness()).toBeFalse();

    await harness.setFilterMode('All');
    expect(await harness.hasAllInputHarness()).toBeTrue();
    expect(await harness.hasPidInputHarness()).toBeFalse();
    expect(await harness.hasRegexInputHarness()).toBeFalse();
  });
});
