import {ComponentHarness} from '@angular/cdk/testing';
import {ApprovalChipHarness} from '../../testing/approval_chip_harness';
import {OnlineChipHarness} from '../../testing/online_chip_harness';

/**
 * Harness for the RecentClientApproval component.
 */
export class RecentClientApprovalHarness extends ComponentHarness {
  static hostSelector = 'recent-client-approval';

  readonly clientLink = this.locatorFor('a');
  readonly approvalChip = this.locatorFor(ApprovalChipHarness);
  readonly onlineChip = this.locatorFor(OnlineChipHarness);
  readonly approvalReason = this.locatorFor('.reason');
}
