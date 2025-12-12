import {ComponentHarness} from '@angular/cdk/testing';

import {UserHarness} from '../../../shared/testing/user_harness';

/** Harness for the GrantedApproval component. */
export class GrantedApprovalHarness extends ComponentHarness {
  static hostSelector = 'granted-approval';

  /**
   * Returns the list of user harnesses displayed for the approvers.
   */
  readonly approvers = this.locatorForAll(UserHarness);

  private readonly reason = this.locatorFor('.reason');

  /**
   * Returns the text of the reason.
   */
  async getReasonText(): Promise<string> {
    const reasonWithText = await this.reason();
    return reasonWithText.text();
  }
}
