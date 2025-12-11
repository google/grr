import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {
  createFileSizeRangeFormGroup,
  FileSizeRangeSubform,
} from './file_size_range_subform';
import {FileSizeRangeSubformHarness} from './testing/file_size_range_subform_harness';

initTestEnvironment();

@Component({
  selector: 'file-size-range-subform-test',
  template: `
    <form [formGroup]="formGroup">
      <file-size-range-subform [formGroup]="formGroup.controls.size"/>
    </form>
  `,
  imports: [CommonModule, FileSizeRangeSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    size: createFileSizeRangeFormGroup(),
  });
}

async function createComponent() {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FileSizeRangeSubformHarness,
  );
  return {fixture, harness};
}

describe('File Size Range Subform component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, FileSizeRangeSubform],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('displays correctly filled min and max file size fields when initialized', async () => {
    const {harness} = await createComponent();

    const minFileSizeInput = await harness.minFileSizeInput();
    expect(await minFileSizeInput.getValue()).toBe('');
    const maxFileSizeInput = await harness.maxFileSizeInput();
    expect(await maxFileSizeInput.getValue()).toBe('20 MB');
  });

  it('exposes form values and shows correct hint when only minimum file size field is filled', async () => {
    const {harness, fixture} = await createComponent();

    const minFileSizeInput = await harness.minFileSizeInput();
    await minFileSizeInput.setValue('10 MB');
    const maxFileSizeInput = await harness.maxFileSizeInput();
    await maxFileSizeInput.setValue('');

    expect(fixture.componentInstance.formGroup.controls.size.value).toEqual({
      minFileSize: 10_000_000,
      maxFileSize: undefined,
    });

    const minFileSizeFormField = await harness.minFileSizeFormField();
    expect(await minFileSizeFormField.getTextHints()).toEqual([
      'Collect files larger than 10,000,000 bytes.',
    ]);

    const maxFileSizeFormField = await harness.maxFileSizeFormField();
    expect(await maxFileSizeFormField.getTextHints()).toEqual([]);
  });

  it('exposes form values and shows correct hint when both fields are filled', async () => {
    const {harness, fixture} = await createComponent();

    const minFileSizeInput = await harness.minFileSizeInput();
    await minFileSizeInput.setValue('10 MB');
    const maxFileSizeInput = await harness.maxFileSizeInput();
    await maxFileSizeInput.setValue('10 GiB');

    expect(fixture.componentInstance.formGroup.controls.size.value).toEqual({
      minFileSize: 10_000_000,
      maxFileSize: 10_737_418_240,
    });

    const minFileSizeFormField = await harness.minFileSizeFormField();
    expect(await minFileSizeFormField.getTextHints()).toEqual([
      'Collect files larger than 10,000,000 bytes.',
    ]);

    const maxFileSizeFormField = await harness.maxFileSizeFormField();
    expect(await maxFileSizeFormField.getTextHints()).toEqual([
      'Collect files smaller than 10,737,418,240 bytes.',
    ]);
  });

  it('shows form error when input value of 0 is entered', async () => {
    const {fixture, harness} = await createComponent();

    const minFileSizeInput = await harness.minFileSizeInput();
    await minFileSizeInput.setValue('0');
    const maxFileSizeInput = await harness.maxFileSizeInput();
    await maxFileSizeInput.setValue('0');

    fixture.componentInstance.formGroup.markAllAsTouched();
    fixture.detectChanges();

    const minFileSizeFormField = await harness.minFileSizeFormField();
    expect(await minFileSizeFormField.getTextErrors()).toEqual([
      'Minimum value is 1.',
    ]);
    const maxFileSizeFormField = await harness.maxFileSizeFormField();
    expect(await maxFileSizeFormField.getTextErrors()).toEqual([
      'Minimum value is 1.',
    ]);
  });

  it('shows error message when neither fields are filled', async () => {
    const {harness} = await createComponent();

    const minFileSizeInput = await harness.minFileSizeInput();
    await minFileSizeInput.setValue('');
    const maxFileSizeInput = await harness.maxFileSizeInput();
    await maxFileSizeInput.setValue('');

    const formErrors = await harness.formErrors();
    expect(await formErrors.length).toBe(1);
    expect(await formErrors[0].getErrorMessages()).toEqual([
      'At least one input must be set.',
    ]);
  });
});
