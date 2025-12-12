import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the OnlineNotificationForm component. */
export class OnlineNotificationFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'online-notification-form';

  private readonly emailInputHarness = this.locatorFor(MatInputHarness);

  /** Sets the email input value. */
  async setEmailInput(email: string): Promise<void> {
    const emailInputHarness = await this.emailInputHarness();
    await emailInputHarness.setValue(email);
  }

  /** Returns the email input value. */
  async getEmailInput(): Promise<string> {
    const emailInputHarness = await this.emailInputHarness();
    return emailInputHarness.getValue();
  }
}
