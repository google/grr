import {ComponentHarness} from '@angular/cdk/testing';
import {MatChipHarness} from '@angular/material/chips/testing';

/** Harness for the ApprovalChip component. */
export class ApprovalChipHarness extends ComponentHarness {
  static hostSelector = 'approval-chip';

  private readonly accessPendingChip = this.locatorForOptional(
    MatChipHarness.with({text: 'Request sent, waiting'}),
  );

  private readonly accessGrantedChip = this.locatorForOptional(
    MatChipHarness.with({text: /^Access granted.*/}),
  );

  private readonly accessDeniedChip = this.locatorForOptional(
    MatChipHarness.with({text: 'No access'}),
  );

  async isAccessPendingChipVisible(): Promise<boolean> {
    return !!(await this.accessPendingChip());
  }

  async isAccessGrantedChipVisible(): Promise<boolean> {
    return !!(await this.accessGrantedChip());
  }

  async getAccessGrantedChipText(): Promise<string> {
    return (await this.accessGrantedChip())?.getText() ?? '';
  }

  async isAccessDeniedChipVisible(): Promise<boolean> {
    return !!(await this.accessDeniedChip());
  }
}
