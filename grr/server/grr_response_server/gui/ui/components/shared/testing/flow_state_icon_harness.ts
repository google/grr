import {ComponentHarness} from '@angular/cdk/testing';
import {MatBadgeHarness} from '@angular/material/badge/testing';
import {MatIconHarness} from '@angular/material/icon/testing';

/** Harness for the FlowStateIcon component. */
export class FlowStateIconHarness extends ComponentHarness {
  static hostSelector = 'flow-state-icon';

  readonly runningIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'hourglass_top'}),
  );
  readonly finishedIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'check_circle'}),
  );
  readonly errorIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'error_outline'}),
  );

  async badgeText(): Promise<string | undefined> {
    return (await this.locatorForOptional(MatBadgeHarness)())?.getText();
  }

  async hasBadge(): Promise<boolean> {
    return !!(await this.locatorForOptional(MatBadgeHarness)());
  }
}
