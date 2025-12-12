import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {LaunchBinaryArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {Binary, BinaryType} from '../../../lib/models/flow';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {LaunchBinaryForm} from './launch_binary_form';
import {LaunchBinaryFormHarness} from './testing/launch_binary_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(LaunchBinaryForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    LaunchBinaryFormHarness,
  );
  return {fixture, harness};
}

describe('Launch Binary Form Component', () => {
  let globalStore: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStore = {
      ...newGlobalStoreMock(),
      fetchBinaryNames: jasmine.createSpy('fetchBinaryNames'),
    };
    TestBed.configureTestingModule({
      imports: [LaunchBinaryForm, NoopAnimationsModule],
      providers: [
        {provide: GlobalStore, useValue: globalStore},
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
    globalStore.executables = signal([
      {path: 'my/awesome/hack.exe', type: BinaryType.EXECUTABLE} as Binary,
    ]);
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('LaunchBinary');
        expect(flowArgs).toEqual({
          binary: 'aff4:/config/executables/my/awesome/hack.exe',
          commandLine: 'foo bar baz',
        });
        onSubmitCalled = true;
      },
    );
    await harness.setBinaryName('my/awesome/hack.exe');
    await harness.setCommandLine('foo bar baz');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      binary: 'my/awesome/hack.exe',
      commandLine: 'foo bar baz',
    });

    const expectedFlowArgs: LaunchBinaryArgs = {
      binary: 'aff4:/config/executables/my/awesome/hack.exe',
      commandLine: 'foo bar baz',
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: LaunchBinaryArgs = {
      binary: 'aff4:/config/executables/my/awesome/hack.exe',
      commandLine: 'foo bar baz',
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      binary: 'my/awesome/hack.exe',
      commandLine: 'foo bar baz',
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      binary: 'my/awesome/hack.py',
      commandLine: 'foo bar baz',
    });
    expect(await harness.getBinaryName()).toBe('my/awesome/hack.py');
    expect(await harness.getCommandLine()).toBe('foo bar baz');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('calls fetchBinaryNames', async () => {
    await createComponent();
    expect(globalStore.fetchBinaryNames).toHaveBeenCalled();
  });

  it('shows the binary paths suggestions in the binary name input', async () => {
    globalStore.executables = signal([
      {path: 'my/awesome/hack.exe', type: BinaryType.EXECUTABLE} as Binary,
      {path: 'my/awesome/hack2.exe', type: BinaryType.EXECUTABLE} as Binary,
    ]);
    const {harness} = await createComponent();
    await harness.setBinaryName('my/awesome/hack');
    const inputHarness = await harness.binaryNameInput();
    const options = await inputHarness.getOptions();
    expect(options.length).toBe(2);
    expect(await options[0].getText()).toBe('my/awesome/hack.exe');
    expect(await options[1].getText()).toBe('my/awesome/hack2.exe');
  });

  it('validates if executable path is valid', async () => {
    globalStore.executables = signal([
      {path: 'my/awesome/hack.exe', type: BinaryType.PYTHON_HACK} as Binary,
    ]);

    const {harness, fixture} = await createComponent();
    await harness.setBinaryName('my/awesome/hack.exe');
    const submitButton = await harness.getSubmitButton();
    expect(fixture.componentInstance.controls.binary.invalid).toBeFalse();
    expect(await submitButton.isDisabled()).toBeFalse();

    await harness.setBinaryName('any/unknown/path.exe');
    expect(fixture.componentInstance.controls.binary.invalid).toBeTrue();
    expect(await submitButton.isDisabled()).toBeTrue();
  });
});
