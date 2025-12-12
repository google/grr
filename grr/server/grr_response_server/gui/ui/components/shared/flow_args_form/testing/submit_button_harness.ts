import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

/** Harness for the SubmitButton component. */
export class SubmitButtonHarness extends ComponentHarness {
  static hostSelector = 'submit-button';

  readonly submitButton = this.locatorFor(MatButtonHarness);

  /** Clicks the submit button. */
  async submit(): Promise<void> {
    return (await this.submitButton()).click();
  }

  /** Returns true if the submit button is disabled. */
  async isDisabled(): Promise<boolean> {
    return (await this.submitButton()).isDisabled();
  }

  /** Returns true if the submit button is enabled. */
  async isEnabled(): Promise<boolean> {
    return (await (await this.submitButton()).isDisabled()) === false;
  }
}
