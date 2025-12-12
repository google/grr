import {ComponentHarness} from '@angular/cdk/testing';
import {MatChipHarness} from '@angular/material/chips/testing';

/** Harness for the OnlineChip component. */
export class OnlineChipHarness extends ComponentHarness {
  static hostSelector = 'online-chip';

  private readonly onlineChip = this.locatorForOptional(
    MatChipHarness.with({text: 'Online'}),
  );

  private readonly offlineChip = this.locatorForOptional(
    MatChipHarness.with({text: 'Offline'}),
  );

  async hasOnlineChip() {
    return !!(await this.onlineChip());
  }

  async hasOfflineChip() {
    return !!(await this.offlineChip());
  }
}
