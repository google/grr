import {ComponentHarness} from '@angular/cdk/testing';

import {FleetCollectionLogsHarness} from './fleet_collection_logs_harness';

/** Harness for the FleetCollectionDebugging component. */
export class FleetCollectionDebuggingHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-debugging';

  readonly fleetCollectionLogs = this.locatorFor(FleetCollectionLogsHarness);
}
