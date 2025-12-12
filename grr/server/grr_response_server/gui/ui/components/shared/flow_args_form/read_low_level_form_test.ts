import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ReadLowLevelArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {ReadLowLevelForm} from './read_low_level_form';
import {ReadLowLevelFormHarness} from './testing/read_low_level_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ReadLowLevelForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ReadLowLevelFormHarness,
  );
  return {fixture, harness};
}

describe('Read Low Level Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ReadLowLevelForm, NoopAnimationsModule],
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
        expect(flowName).toBe('ReadLowLevel');
        expect(flowArgs).toEqual({
          path: '/some/path',
          length: '1000000',
          offset: '12',
        });
        onSubmitCalled = true;
      },
    );

    await harness.setPathInput('/some/path');
    await harness.setLengthInput('1 MB');
    await harness.setOffsetInput('12 B');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      path: '/some/path',
      length: 1048576,
      offset: 12,
    });

    const expectedFlowArgs: ReadLowLevelArgs = {
      path: '/some/path',
      length: '1048576',
      offset: '12',
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ReadLowLevelArgs = {
      path: '/some/path',
      length: '1000000',
      offset: '12',
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      path: '/some/path',
      length: 1_000_000,
      offset: 12,
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness} = await createComponent({
      path: '/some/path',
      length: 1_000_000,
      offset: 12,
    });

    expect(await harness.getPathInput()).toBe('/some/path');
    expect(await harness.getLengthInput()).toBe('1 MB');
    expect(await harness.getOffsetInput()).toBe('12 B');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('displays input fields with default values', async () => {
    const {harness} = await createComponent();

    expect(await harness.getPathInput()).toBe('');
    expect(await harness.getLengthInput()).toBe('42 B');
    expect(await harness.getOffsetInput()).toBe('0 B');
  });

  it('ddisplays no errors when path and length are valid', async () => {
    const {harness} = await createComponent();
    await harness.setPathInput('/some/path');
    await harness.setLengthInput('10');

    expect(await harness.getPathErrors()).toEqual([]);
    expect(await harness.getLengthErrors()).toEqual([]);
  });

  it('displays error when path and length are empty', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setPathInput('');
    await harness.setLengthInput('');

    fixture.componentInstance.controls.path.markAllAsTouched();
    fixture.componentInstance.controls.length.markAllAsTouched();
    fixture.detectChanges();

    expect(await harness.getPathErrors()).toEqual(['Input is required.']);
    expect(await harness.getLengthErrors()).toEqual(['Input is required.']);
  });

  it('displays error when length is less than one', async () => {
    const {harness, fixture} = await createComponent();
    await harness.setLengthInput('0');

    fixture.componentInstance.controls.length.markAllAsTouched();
    fixture.detectChanges();

    expect(await harness.getLengthErrors()).toEqual(['Minimum value is 1.']);
  });

  it('trims tabs, spaces and linebreaks in path input when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowArgs).toEqual({
          path: '/some/path',
          length: '42',
          offset: '0',
        });
        onSubmitCalled = true;
      },
    );

    await harness.setPathInput('         /some/path\n\t');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });
});
