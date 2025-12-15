import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the FormValidation.FormErrors component. */
export class FormErrorsHarness extends ComponentHarness {
  static hostSelector = 'form-errors';

  /** All error messages. */
  readonly errors = this.locatorForAll('span');

  /** Gets the texts of all error messages. */
  async getErrorMessages(): Promise<string[]> {
    const errors = await this.errors();
    return Promise.all(errors.map((error) => error.text()));
  }
}

/** Harness for the FormValidation.FormWarnings component. */
export class FormWarningsHarness extends ComponentHarness {
  static hostSelector = 'form-warnings';

  /** All warning messages. */
  readonly warnings = this.locatorForAll('span');

  /** Gets the texts of all warning messages. */
  async getWarningMessages(): Promise<string[]> {
    const warnings = await this.warnings();
    return Promise.all(warnings.map((warning) => warning.text()));
  }
}
