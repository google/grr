import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {InterrogateArgs} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {InterrogateForm} from './interrogate_form';
import {InterrogateFormHarness} from './testing/interrogate_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(InterrogateForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    InterrogateFormHarness,
  );
  return {fixture, harness};
}

describe('Interrogate Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [InterrogateForm, NoopAnimationsModule],
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
        expect(flowName).toBe('Interrogate');
        expect(flowArgs).toEqual({});
        onSubmitCalled = true;
      },
    );

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({});

    const expectedFlowArgs: InterrogateArgs = {};
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: InterrogateArgs = {};

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({});
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });
});
