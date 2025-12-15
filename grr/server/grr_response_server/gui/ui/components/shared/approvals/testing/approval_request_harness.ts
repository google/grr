import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCardHarness} from '@angular/material/card/testing';

/** Harness for the ApprovalRequest component. */
export class ApprovalRequestHarness extends ComponentHarness {
  static hostSelector = 'approval-request';

  readonly approvalCard = this.locatorFor(MatCardHarness);

  async getGrantApprovalButton(): Promise<MatButtonHarness> {
    const approvalCard = await this.approvalCard();
    if (!approvalCard) {
      throw new Error('Approval card is not present');
    }
    return approvalCard.getHarness(MatButtonHarness);
  }
}
