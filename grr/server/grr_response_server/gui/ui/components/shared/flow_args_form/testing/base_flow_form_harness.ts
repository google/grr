import {ComponentHarness} from '@angular/cdk/testing';

import {SubmitButtonHarness} from './submit_button_harness';

/** Base Harness for the FlowArgsForm components. */
export class BaseFlowFormHarness extends ComponentHarness {
  static hostSelector = 'flow-args-form';

  readonly submitButton = this.locatorForOptional(SubmitButtonHarness);

  async hasSubmitButton(): Promise<boolean> {
    return !!(await this.submitButton());
  }

  async getSubmitButton(): Promise<SubmitButtonHarness> {
    const submitButton = await this.submitButton();
    if (!submitButton) {
      throw new Error('Submit button is not available.');
    }
    return submitButton;
  }
}
