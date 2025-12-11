import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ListNamedPipesFlowArgs,
  ListNamedPipesFlowArgsPipeEndFilter,
  ListNamedPipesFlowArgsPipeTypeFilter,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {ListNamedPipesForm} from './list_named_pipes_form';
import {ListNamedPipesFormHarness} from './testing/list_named_pipes_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ListNamedPipesForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ListNamedPipesFormHarness,
  );
  return {fixture, harness};
}

describe('List Named Pipes Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ListNamedPipesForm, NoopAnimationsModule],
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
        expect(flowName).toBe('ListNamedPipesFlow');
        expect(flowArgs).toEqual({
          pipeNameRegex: 'pipe1',
          procExeRegex: 'proc1',
          pipeTypeFilter: 'MESSAGE_TYPE',
          pipeEndFilter: 'SERVER_END',
        });
        onSubmitCalled = true;
      },
    );
    await harness.setPipeNameInput('pipe1');
    await harness.setProcessExecutableInput('proc1');
    await harness.selectPipeType('Only message');
    await harness.selectPipeEnd('Only server');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      pipeNameRegex: 'pipe1',
      procExeRegex: 'proc1',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.MESSAGE_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.SERVER_END,
    });

    const expectedFlowArgs: ListNamedPipesFlowArgs = {
      pipeNameRegex: 'pipe1',
      procExeRegex: 'proc1',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.MESSAGE_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.SERVER_END,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListNamedPipesFlowArgs = {
      pipeNameRegex: 'pipe1',
      procExeRegex: 'proc1',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.MESSAGE_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.SERVER_END,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      pipeNameRegex: 'pipe1',
      procExeRegex: 'proc1',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.MESSAGE_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.SERVER_END,
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      pipeNameRegex: 'pipe1',
      procExeRegex: 'proc1',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.MESSAGE_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.SERVER_END,
    });
    expect(await harness.getPipeNameInputText()).toBe('pipe1');
    expect(await harness.getProcessExecutableInputText()).toBe('proc1');
    expect(await harness.getSelectedPipeType()).toBe('Only message');
    expect(await harness.getSelectedPipeEnd()).toBe('Only server');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });
});
