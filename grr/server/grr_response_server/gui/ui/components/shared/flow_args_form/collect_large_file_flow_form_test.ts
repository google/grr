import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectLargeFileFlowArgs,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {CollectLargeFileFlowForm} from './collect_large_file_flow_form';
import {CollectLargeFileFlowFormHarness} from './testing/collect_large_file_flow_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectLargeFileFlowFormHarness,
  );
  return {fixture, harness};
}

describe('Collect Large File Flow Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectLargeFileFlowForm, NoopAnimationsModule],
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
        expect(flowName).toBe('CollectLargeFileFlow');
        expect(flowArgs).toEqual({
          pathSpec: {
            path: '/some/path',
            pathtype: PathSpecPathType.OS,
          },
          signedUrl: 'http://signed/url',
        });
        onSubmitCalled = true;
      },
    );
    await harness.setPathInput('/some/path');
    await harness.setPathType('OS');
    await harness.setSignedUrlInput('http://signed/url');

    const submitButton = await harness.getSubmitButton();

    await submitButton.submit();
    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      path: '/some/path/with/trailing/spaces/tabs/and/linebreaks \n \t\n   ',
      pathtype: PathSpecPathType.OS,
      signedUrl: '   http://signed/url/with/trailing/spaces   ',
    });

    const expectedFlowArgs: CollectLargeFileFlowArgs = {
      pathSpec: {
        path: '/some/path/with/trailing/spaces/tabs/and/linebreaks',
        pathtype: PathSpecPathType.OS,
      },
      signedUrl: 'http://signed/url/with/trailing/spaces',
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: CollectLargeFileFlowArgs = {
      pathSpec: {
        path: '/some/path',
        pathtype: PathSpecPathType.OS,
      },
      signedUrl: 'http://signed/url',
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      path: '/some/path',
      pathtype: PathSpecPathType.OS,
      signedUrl: 'http://signed/url',
    });
  });

  it('resets the flow args when passing flowArgs', fakeAsync(async () => {
    const {harness} = await createComponent({
      pathSpec: {
        path: '/some/path',
        pathtype: PathSpecPathType.TSK,
      },
      signedUrl: 'http://signed/url/123',
    });
    tick();
    expect(await harness.getPathInput()).toBe('/some/path');
    expect(await harness.getSelectedPathTypeText()).toBe('TSK');
    expect(await harness.getSignedUrlInput()).toBe('http://signed/url/123');
  }));

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('initializes the path type to OS', async () => {
    const {harness} = await createComponent();
    expect(await harness.getSelectedPathTypeText()).toBe('OS');
  });

  it('displays error when input is missing', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.controls.path.markAllAsTouched();
    fixture.detectChanges();

    expect(await harness.hasInputError()).toBeTrue();
  });

  it('does not display error when input is valid', async () => {
    const {harness} = await createComponent();

    await harness.setPathInput('/some/path');
    await harness.setPathType('OS');
    await harness.setSignedUrlInput('http://signed/url');

    expect(await harness.hasInputError()).toBeFalse();
  });
});
