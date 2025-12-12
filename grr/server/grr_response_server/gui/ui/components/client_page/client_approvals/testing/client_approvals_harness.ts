import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

import {ApprovalRequestHarness} from '../../../shared/approvals/testing/approval_request_harness';
import {GrantedApprovalHarness} from '../../../shared/approvals/testing/granted_approval_harness';
import {PendingApprovalHarness} from '../../../shared/approvals/testing/pending_approval_harness';
import {ClientApprovalFormHarness} from './client_approval_form_harness';

/** Harness for the ClientApprovals component. */
export class ClientApprovalsHarness extends ComponentHarness {
  static hostSelector = 'client-approvals';

  readonly approvalRequest = this.locatorForOptional(ApprovalRequestHarness);

  private readonly approvalForm = this.locatorForOptional(
    ClientApprovalFormHarness,
  );

  private readonly pendingApproval = this.locatorForAll(PendingApprovalHarness);

  private readonly grantedApproval = this.locatorForOptional(
    GrantedApprovalHarness,
  );

  private readonly showApprovalFormButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'Send new approval request'}),
  );

  async isApprovalRequestVisible(): Promise<boolean> {
    return !!(await this.approvalRequest());
  }

  async isApprovalFormVisible(): Promise<boolean> {
    return !!(await this.approvalForm());
  }

  async isPendingApprovalVisible(): Promise<boolean> {
    return (await this.pendingApproval()).length > 0;
  }

  async numberOfPendingApprovals(): Promise<number> {
    return (await this.pendingApproval()).length;
  }

  async isGrantedApprovalVisible(): Promise<boolean> {
    return !!(await this.grantedApproval());
  }

  async isShowApprovalFormButtonVisible(): Promise<boolean> {
    return !!(await this.showApprovalFormButton());
  }

  async clickShowApprovalFormButton(): Promise<void> {
    const button = await this.showApprovalFormButton();
    await button?.click();
  }
}
