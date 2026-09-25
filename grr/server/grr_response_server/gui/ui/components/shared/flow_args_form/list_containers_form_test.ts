import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ListContainersFlowArgs} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {ListContainersForm} from './list_containers_form';
import {ListContainersFormHarness} from './testing/list_containers_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ListContainersForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ListContainersFormHarness,
  );
  return {fixture, harness};
}

describe('ListContainers Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ListContainersForm, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('can toggle inspectHostroot checkbox', async () => {
    const {harness} = await createComponent({inspectHostroot: false});
    expect(
      await (await harness.inspectHostrootCheckbox()).isChecked(),
    ).toBeFalse();

    await (await harness.inspectHostrootCheckbox()).check();
    expect(
      await (await harness.inspectHostrootCheckbox()).isChecked(),
    ).toBeTrue();
  });

  it('triggers onSubmit callback when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('ListContainers');
        expect(flowArgs).toEqual({
          inspectHostroot: false,
        });
        onSubmitCalled = true;
      },
    );

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      inspectHostroot: true,
    });

    const expectedFlowArgs: ListContainersFlowArgs = {
      inspectHostroot: true,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListContainersFlowArgs = {
      inspectHostroot: true,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      inspectHostroot: true,
    });
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('converts undefined flow args to default form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListContainersFlowArgs = {};

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      inspectHostroot: false,
    });
  });

  it('converts false flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListContainersFlowArgs = {
      inspectHostroot: false,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      inspectHostroot: false,
    });
  });

  it('populates the form with initial flow args', async () => {
    const {harness} = await createComponent({
      inspectHostroot: true,
    });
    expect(
      await (await harness.inspectHostrootCheckbox()).isChecked(),
    ).toBeTrue();
  });
});
