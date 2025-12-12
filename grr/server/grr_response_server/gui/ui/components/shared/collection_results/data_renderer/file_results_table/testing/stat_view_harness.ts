import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the StatView component. */
export class StatViewHarness extends ComponentHarness {
  static hostSelector = 'stat-view';

  readonly detailsTable = this.locatorFor('.details');
  readonly statTable = this.locatorFor('.stat-table');
  readonly hashesTable = this.locatorForOptional('.hashes-table');
}
