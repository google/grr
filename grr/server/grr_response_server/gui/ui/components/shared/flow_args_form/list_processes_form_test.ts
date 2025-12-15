import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ListProcessesArgs,
  NetworkConnectionState,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {CONNECTION_STATES, ListProcessesForm} from './list_processes_form';
import {ListProcessesFormHarness} from './testing/list_processes_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ListProcessesForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ListProcessesFormHarness,
  );
  return {fixture, harness};
}

describe('List Processes Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ListProcessesForm, NoopAnimationsModule],
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
        expect(flowName).toBe('ListProcesses');
        expect(flowArgs).toEqual({
          filenameRegex: '^/usr/(local/)?bin/foo.+$',
          pids: [0, 42, 123],
          connectionStates: ['CLOSE', 'ESTABLISHED'],
          fetchBinaries: true,
        });
        onSubmitCalled = true;
      },
    );
    await harness.setFilenameRegex('^/usr/(local/)?bin/foo.+$');
    await harness.setPids('0, 42, 123');
    await harness.setConnectionStates(['CLOSE', 'ESTABLISHED']);
    await harness.setFetchBinariesCheckbox(true);

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      filenameRegex: '^/usr/(local/)?bin/foo.+$',
      pids: [0, 42, 123],
      connectionStates: [
        NetworkConnectionState.CLOSE,
        NetworkConnectionState.ESTABLISHED,
      ],
      fetchBinaries: true,
    });

    const expectedFlowArgs: ListProcessesArgs = {
      filenameRegex: '^/usr/(local/)?bin/foo.+$',
      pids: [0, 42, 123],
      connectionStates: [
        NetworkConnectionState.CLOSE,
        NetworkConnectionState.ESTABLISHED,
      ],
      fetchBinaries: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListProcessesArgs = {
      filenameRegex: '^/usr/(local/)?bin/foo.+$',
      pids: [0, 42, 123],
      connectionStates: [
        NetworkConnectionState.CLOSE,
        NetworkConnectionState.ESTABLISHED,
      ],
      fetchBinaries: true,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      filenameRegex: '^/usr/(local/)?bin/foo.+$',
      pids: [0, 42, 123],
      connectionStates: [
        NetworkConnectionState.CLOSE,
        NetworkConnectionState.ESTABLISHED,
      ],
      fetchBinaries: true,
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      filenameRegex: '^/usr/(local/)?bin/foo.+$',
      pids: [0, 42, 123],
      connectionStates: [
        NetworkConnectionState.CLOSE,
        NetworkConnectionState.ESTABLISHED,
      ],
      fetchBinaries: true,
    });
    expect(await harness.getFilenameRegex()).toBe('^/usr/(local/)?bin/foo.+$');
    expect(await harness.getPids()).toBe('0, 42, 123');
    expect(await harness.getConnectionState()).toEqual([
      'CLOSE',
      'ESTABLISHED',
    ]);
    expect(await harness.getFetchBinariesCheckbox()).toBeTrue();
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('shows connection state suggestions', async () => {
    const {harness} = await createComponent();

    expect(await harness.getConnectionStateSuggestionTexts()).toEqual(
      CONNECTION_STATES,
    );
  });

  it('filters connection state suggestions by input', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStateInput('ESTABLISHED');

    expect(await harness.getConnectionStateSuggestionTexts()).toEqual([
      'ESTABLISHED',
    ]);
  });

  it('filters connection state suggestions by input ignoring case', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStateInput('established');

    expect(await harness.getConnectionStateSuggestionTexts()).toEqual([
      'ESTABLISHED',
    ]);
  });

  it('shows error if pid input is not a list of numbers', async () => {
    const {harness} = await createComponent();
    await harness.setPids('foo');

    expect(await harness.getPidsErrors()).toEqual(['Invalid integer list.']);
  });

  it('filters connection state suggestions by selected states', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStates(['CLOSE']);
    await harness.setConnectionStateInput('CLOSE');

    expect(await harness.getConnectionStateSuggestionTexts()).toEqual([
      'CLOSED',
      'CLOSE_WAIT',
    ]);
  });

  it('adds connection state when input matches a suggestion', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStateInputAndEnter('ESTABLISHED');

    expect(await harness.getConnectionState()).toEqual(['ESTABLISHED']);
    expect(await harness.getConnectionStateInput()).toBe('');
  });

  it('does not add connection state when input does not match a suggestion', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStateInputAndEnter('NOT_A_STATE');

    expect(await harness.getConnectionState()).toEqual([]);
    expect(await harness.getConnectionStateInput()).toBe('NOT_A_STATE');
  });

  it('adds connection state when selected from suggestions', async () => {
    const {harness} = await createComponent();

    const options = await harness.getConnectionStateSuggestionOptions();
    await options[0].click();

    expect(await harness.getConnectionState()).toEqual([CONNECTION_STATES[0]]);
  });

  it('clear input when adding connection state from suggestions', async () => {
    const {harness} = await createComponent();

    await harness.setConnectionStateInput('ESTABLISHED');
    const options = await harness.getConnectionStateSuggestionOptions();
    await options[0].click();

    expect(await harness.getConnectionState()).toEqual(['ESTABLISHED']);
    expect(await harness.getConnectionStateInput()).toBe('');
  });
});
