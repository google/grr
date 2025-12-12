import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectFilesByKnownPathArgs,
  CollectFilesByKnownPathArgsCollectionLevel,
} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {CollectFilesByKnownPathForm} from './collect_files_by_known_path_form';
import {CollectFilesByKnownPathFormHarness} from './testing/collect_files_by_known_path_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectFilesByKnownPathFormHarness,
  );
  return {fixture, harness};
}

describe('Collect Files By Known Path Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectFilesByKnownPathForm, NoopAnimationsModule],
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
        expect(flowName).toBe('CollectFilesByKnownPath');
        expect(flowArgs).toEqual({
          paths: ['/some/path', '/another/path'],
          collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.STAT,
        });
        onSubmitCalled = true;
      },
    );
    await harness.setPathsInput('/some/path\n/another/path');
    await harness.expandAdvancedParams();
    await harness.setActiveCollectionLevel('Collect file(s) stat');
    const submitButton = await harness.getSubmitButton();

    await submitButton.submit();
    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      paths: '/some/path\n /another/path/with/trailing/spaces   ',
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.HASH,
    });

    const expectedFlowArgs: CollectFilesByKnownPathArgs = {
      paths: ['/some/path', '/another/path/with/trailing/spaces'],
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.HASH,
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: CollectFilesByKnownPathArgs = {
      paths: ['/some/path', '/another/path'],
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      paths: '/some/path\n/another/path',
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    });
  });

  it('resets the flow args when passing flowArgs', async () => {
    const {harness} = await createComponent({
      paths: ['/some/path', 'another/path'],
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    });
    expect(await harness.getPathsInput()).toBe('/some/path\nanother/path');
    await harness.expandAdvancedParams();
    expect(await harness.getActiveCollectionLevelText()).toContain(
      'Collect entire file(s)',
    );
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('displays error when input is empty', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.controls.paths.markAllAsTouched();
    fixture.detectChanges();

    expect(await harness.hasInputError()).toBeTrue();
    const inputError = await harness.inputError();
    expect(await inputError!.getErrorMessages()).toEqual([
      'Input is required.',
    ]);
  });

  it('does not display error when input is valid', async () => {
    const {harness} = await createComponent();
    await harness.setPathsInput('/some/path');

    expect(await harness.hasInputError()).toBeFalse();
  });

  it('hides advanced params by default', async () => {
    const {harness} = await createComponent();
    expect(await harness.isAdvancedParamsVisible()).toBeFalse();
  });

  it('shows/hides advanced params when expanded/collapsed', async () => {
    const {harness} = await createComponent();

    expect(await harness.isAdvancedParamsVisible()).toBeFalse();
    await harness.expandAdvancedParams();
    expect(await harness.isAdvancedParamsVisible()).toBeTrue();
    await harness.collapseAdvancedParams();
    expect(await harness.isAdvancedParamsVisible()).toBeFalse();
  });

  it('collects entire file by default', async () => {
    const {harness} = await createComponent();
    await harness.expandAdvancedParams();

    expect(await harness.getActiveCollectionLevelText()).toContain(
      'Collect entire file(s)',
    );
  });
});
