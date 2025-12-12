import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the ClientRegexForm component. */
export class ClientRegexFormHarness extends ComponentHarness {
  static hostSelector = 'client-regex-form';

  readonly regexInput = this.locatorFor(MatInputHarness);

  async getRegexInput(): Promise<string> {
    return (await this.regexInput()).getValue();
  }

  async setRegexInput(value: string): Promise<void> {
    return (await this.regexInput()).setValue(value);
  }
}
