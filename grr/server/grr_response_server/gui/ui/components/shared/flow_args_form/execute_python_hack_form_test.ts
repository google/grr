import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ExecutePythonHackArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {Binary, BinaryType} from '../../../lib/models/flow';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ExecutePythonHackForm} from './execute_python_hack_form';
import {ExecutePythonHackFormHarness} from './testing/execute_python_hack_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ExecutePythonHackForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExecutePythonHackFormHarness,
  );
  return {fixture, harness};
}

describe('Execute Python Hack Form Component', () => {
  let globalStore: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStore = {
      ...newGlobalStoreMock(),
      fetchBinaryNames: jasmine.createSpy('fetchBinaryNames'),
    };
    TestBed.configureTestingModule({
      imports: [ExecutePythonHackForm, NoopAnimationsModule],
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
    globalStore.pythonHacks = signal([
      {path: 'my/awesome/hack.py', type: BinaryType.PYTHON_HACK} as Binary,
    ]);
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('ExecutePythonHack');
        expect(flowArgs).toEqual({
          hackName: 'my/awesome/hack.py',
          pyArgs: {
            dat: [
              {
                k: {string: 'key1'},
                v: {string: 'value1'},
              },
              {
                k: {string: 'key2'},
                v: {string: 'value2'},
              },
              {
                k: {string: ''},
                v: {string: ''},
              },
            ],
          },
        });
        onSubmitCalled = true;
      },
    );
    await harness.setHackName('my/awesome/hack.py');
    await harness.addKeyValueArgument();
    await harness.setKeyValueArgument(0, 'key1', 'value1');
    await harness.addKeyValueArgument();
    await harness.setKeyValueArgument(1, 'key2', 'value2');
    await harness.addKeyValueArgument();

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      hackName: 'my/awesome/hack.py',
      pyArgs: [
        {key: 'key1', value: 'value1'},
        {key: 'key2', value: 'value2'},
      ],
    });

    const expectedFlowArgs: ExecutePythonHackArgs = {
      hackName: 'my/awesome/hack.py',
      pyArgs: {
        dat: [
          {k: {string: 'key1'}, v: {string: 'value1'}},
          {k: {string: 'key2'}, v: {string: 'value2'}},
        ],
      },
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ExecutePythonHackArgs = {
      hackName: 'my/awesome/hack.py',
      pyArgs: {
        dat: [
          {k: {string: 'key1'}, v: {string: 'value1'}},
          {k: {string: 'key2'}, v: {string: 'value2'}},
        ],
      },
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      hackName: 'my/awesome/hack.py',
      pyArgs: [
        {key: 'key1', value: 'value1'},
        {key: 'key2', value: 'value2'},
      ],
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      hackName: 'my/awesome/hack.py',
      pyArgs: {
        dat: [
          {k: {string: 'key1'}, v: {string: 'value1'}},
          {k: {string: 'key2'}, v: {string: 'value2'}},
        ],
      },
    });
    const hackNameInput = await harness.hackNameInput();
    expect(await hackNameInput.getValue()).toBe('my/awesome/hack.py');

    expect(await harness.getNumberOfKeyValueArguments()).toBe(2);
    expect(await harness.getKeyValueArgument(0)).toEqual(['key1', 'value1']);
    expect(await harness.getKeyValueArgument(1)).toEqual(['key2', 'value2']);
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('calls fetchBinaryNames', async () => {
    await createComponent();
    expect(globalStore.fetchBinaryNames).toHaveBeenCalled();
  });

  it('can add and remove key-value arguments', async () => {
    const {harness} = await createComponent();
    expect(await harness.getNumberOfKeyValueArguments()).toBe(0);
    await harness.addKeyValueArgument();
    expect(await harness.getNumberOfKeyValueArguments()).toBe(1);
    await harness.addKeyValueArgument();
    expect(await harness.getNumberOfKeyValueArguments()).toBe(2);
    await harness.removeKeyValueArgument(1);
    expect(await harness.getNumberOfKeyValueArguments()).toBe(1);
    await harness.removeKeyValueArgument(0);
    expect(await harness.getNumberOfKeyValueArguments()).toBe(0);
  });

  it('shows the binary paths suggestions in the hack name input', async () => {
    globalStore.pythonHacks = signal([
      {path: 'my/awesome/hack.py', type: BinaryType.PYTHON_HACK} as Binary,
      {path: 'my/awesome/hack2.py', type: BinaryType.PYTHON_HACK} as Binary,
    ]);
    const {harness} = await createComponent();
    const hackNameInput = await harness.hackNameInput();
    await hackNameInput.enterText('my/awesome/hack.py');
    const options = await hackNameInput.getOptions();
    expect(options.length).toBe(1);
    expect(await options[0].getText()).toBe('my/awesome/hack.py');
  });

  it('validates if python hack path is valid', async () => {
    globalStore.pythonHacks = signal([
      {path: 'my/awesome/hack.py', type: BinaryType.PYTHON_HACK} as Binary,
    ]);

    const {harness, fixture} = await createComponent();
    await harness.setHackName('my/awesome/hack.py');
    const submitButton = await harness.getSubmitButton();
    expect(fixture.componentInstance.controls.hackName.invalid).toBeFalse();
    expect(await submitButton.isDisabled()).toBeFalse();

    await harness.setHackName('any/unknown/path.py');
    expect(fixture.componentInstance.controls.hackName.invalid).toBeTrue();
    expect(await submitButton.isDisabled()).toBeTrue();
  });
});
