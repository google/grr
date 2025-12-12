import {ComponentHarness} from '@angular/cdk/testing';

import {CopyButtonHarness} from '../../../shared/testing/copy_button_harness';
import {UserHarness} from '../../../shared/testing/user_harness';

/** Harness for the PendingApproval component. */
export class PendingApprovalHarness extends ComponentHarness {
  static hostSelector = 'pending-approval';

  /**
   * Returns the list of user harnesses displayed for the requested approvers.
   */
  readonly requestedApprovers = this.locatorForAll(UserHarness);

  private readonly reason = this.locatorFor('.reason');

  private readonly copyButton = this.locatorFor(CopyButtonHarness);

  /**
   * Returns the text of the reason.
   */
  async getReasonText(): Promise<string> {
    const reasonWithText = await this.reason();
    return reasonWithText.text();
  }

  /**
   * Returns true if the copy button is displayed with the given approval URL.
   */
  async showsCopyButtonWithApprovalUrl(url: RegExp): Promise<boolean> {
    const copyButton = await this.copyButton();
    return (await copyButton.getContentsText()).match(url) !== null;
  }
}
