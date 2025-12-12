import {ComponentHarness} from '@angular/cdk/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {FormErrorsHarness} from '../../../form/testing/form_validation_harness';

/** Harness for the FileSizeRangeSubform component. */
export class FileSizeRangeSubformHarness extends ComponentHarness {
  static hostSelector = 'file-size-range-subform';

  /** Form field for the minimum file size. */
  readonly minFileSizeFormField = this.locatorFor(
    MatFormFieldHarness.with({selector: '.minFileSize'}),
  );

  /** Input field for the minimum file size. */
  readonly minFileSizeInput = this.locatorFor(
    MatInputHarness.with({selector: '[name="minFileSize"]'}),
  );

  /** Form field for the maximum file size. */
  readonly maxFileSizeFormField = this.locatorFor(
    MatFormFieldHarness.with({selector: '.maxFileSize'}),
  );

  /** Input field for the maximum file size. */
  readonly maxFileSizeInput = this.locatorFor(
    MatInputHarness.with({selector: '[name="maxFileSize"]'}),
  );

  /** All form errors. */
  readonly formErrors = this.locatorForAll(FormErrorsHarness);
}
