import {ComponentHarness} from '@angular/cdk/testing';

import {DivHarness} from './div_harness';

/** Harness for the ErrorMessage component. */
export class ErrorMessageHarness extends ComponentHarness {
  static hostSelector = 'error-message';

  readonly message = this.locatorFor(DivHarness);

  async getMessage(): Promise<string> {
    return (await this.message()).getText();
  }
}
