import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the FleetCollectionProgressChart component. */
export class FleetCollectionProgressChartHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-progress-chart';

  readonly noDataBlock = this.locatorForOptional('.no-data');

  readonly svg = this.locatorForOptional('svg');
}
